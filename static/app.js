const MAX_QUESTION_LENGTH = 1000;
const MAX_SOURCES = 3;
const REQUEST_TIMEOUT_MS = 20000;

const questionForm = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const askButton = document.querySelector("#ask");
const exampleButton = document.querySelector("#example");
const fieldError = document.querySelector("#field-error");
const statusLine = document.querySelector("#status");
const resultSection = document.querySelector("#result");
const resultHeading = document.querySelector("#result-heading");
const resultMessage = document.querySelector("#message");
const sourcesContainer = document.querySelector("#sources");

const resultHeadings = {
  answer: "Answer",
  hr_guidance: "Contact HR",
  service_error: "Please try again",
};

function showInputError(text) {
  fieldError.textContent = text;
  fieldError.hidden = false;
  questionInput.setAttribute("aria-invalid", "true");
  questionInput.focus();
}

function isValidSource(source) {
  if (!source) return false;

  const requiredFields = ["document_title", "document_id", "passage_id", "passage_text"];
  for (const fieldName of requiredFields) {
    const fieldValue = source[fieldName];
    if (typeof fieldValue !== "string" || !fieldValue.trim()) return false;
  }

  return true;
}

function isValidReply(reply, httpStatus) {
  if (!reply || typeof reply.message !== "string" || !reply.message.trim()) return false;
  if (!Array.isArray(reply.sources)) return false;

  const resultType = reply.result_type;
  if (resultType === "answer") {
    const sourceCount = reply.sources.length;
    if (httpStatus !== 200 || sourceCount < 1 || sourceCount > MAX_SOURCES) return false;
    return reply.sources.every(isValidSource);
  }

  if (reply.sources.length !== 0) return false;
  if (resultType === "hr_guidance") return httpStatus === 200;
  if (resultType === "input_error") return httpStatus >= 400 && httpStatus < 500;
  if (resultType === "service_error") return httpStatus >= 500;

  return false;
}

function displayResult(reply) {
  resultHeading.textContent = resultHeadings[reply.result_type];
  resultMessage.textContent = reply.message;
  for (const [index, source] of reply.sources.entries()) {
    const sourceDetails = document.createElement("details");
    const sourceSummary = document.createElement("summary");
    const passageText = document.createElement("blockquote");
    sourceSummary.textContent = source.document_title + " · " + source.passage_id;
    passageText.textContent = source.passage_text;
    sourceDetails.open = index === 0;
    sourceDetails.append(sourceSummary, passageText);
    sourcesContainer.append(sourceDetails);
  }
  resultSection.hidden = false;
  resultHeading.focus();
}

function clearFieldError() {
  fieldError.hidden = true;
  fieldError.textContent = "";
  questionInput.removeAttribute("aria-invalid");
}

questionInput.addEventListener("input", clearFieldError);
exampleButton.addEventListener("click", () => {
  questionInput.value = "Where and when is new-hire orientation?";
  clearFieldError();
  questionInput.focus();
});

questionForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (askButton.disabled) return;
  resultSection.hidden = true;
  sourcesContainer.replaceChildren();
  clearFieldError();
  const questionText = questionInput.value.trim();
  if (!questionText) return showInputError("Please enter a question.");
  if ([...questionText].length > MAX_QUESTION_LENGTH) {
    return showInputError("Please use 1,000 characters or fewer.");
  }

  askButton.disabled = true;
  exampleButton.disabled = true;
  questionInput.readOnly = true;
  statusLine.textContent = "Checking the orientation guide…";
  const controller = new AbortController();
  // Allow network travel around the server's shared 15-second deadline.
  const requestTimer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch("/api/questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: questionText }),
      signal: controller.signal,
    });
    const reply = await response.json();
    if (!isValidReply(reply, response.status)) throw new Error("Invalid response");
    if (reply.result_type === "input_error") showInputError(reply.message);
    else displayResult(reply);
  } catch {
    displayResult({
      result_type: "service_error",
      message: "We couldn’t get an answer. Please try again.",
      sources: [],
    });
  } finally {
    clearTimeout(requestTimer);
    askButton.disabled = false;
    exampleButton.disabled = false;
    questionInput.readOnly = false;
    statusLine.textContent = "";
  }
});

askButton.disabled = false;
exampleButton.hidden = false;
