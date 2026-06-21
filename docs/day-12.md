# Day 12 - Quiz Attempts and Scoring

## Goal

Turn generated quiz questions into a complete practice flow: answer questions,
submit an attempt, receive an objective score, and keep the result after a
browser refresh or service restart.

## Data Model

```text
documents
  1 -> many quiz_questions
  1 -> many quiz_attempts
quiz_attempts
  1 -> many quiz_responses
```

`quiz_attempts` stores one submission summary:

- `total_questions`: every question in the quiz
- `scored_questions`: only multiple-choice and true/false questions
- `correct_answers`: objective questions answered correctly
- `created_at`: when the learner submitted

`quiz_responses` stores one answer inside an attempt:

- `attempt_id`: the parent submission
- `quiz_question_id`: which generated question was answered
- `submitted_answer`: the learner's answer, including an empty answer
- `is_correct`: `true`, `false`, or `null`

`null` means the question is a short answer. This first version saves it for
review but does not pretend an exact string comparison can fairly grade it.

## API

```text
GET  /documents/{document_id}/quiz/attempts
POST /documents/{document_id}/quiz/submit
```

The submit request contains an array of objects such as:

```json
{
  "answers": [
    { "question_id": 12, "answer": "Mandatory access control" },
    { "question_id": 13, "answer": "" }
  ]
}
```

The backend loads the question records from PostgreSQL instead of trusting the
browser to send correct answers. It normalizes whitespace and letter case for
objective-question comparison, creates the attempt and response records, then
returns the stored result.

## Frontend State

React stores answers while the learner is typing in this shape:

```ts
Record<number, string>
```

The numeric key is a quiz-question ID and the string is the selected option or
typed short answer. On submission, React maps every visible question into the
JSON payload. This includes unanswered questions as empty strings, so an
attempt always describes the complete quiz.

## Important Lifecycle Rule

Generating a replacement quiz deletes its old questions and old attempts.
Those attempts cannot meaningfully survive because their responses point to
questions that no longer exist. Reprocessing a document has the same effect.

## What To Test

1. Start the stack with `start-dev.cmd`.
2. Open `http://localhost:3000` and choose a document with generated questions.
3. Select objective answers and type a short answer.
4. Click `Submit Quiz`.
5. Confirm the score and a timestamp appear under `Saved attempts`.
6. Refresh the browser, click the document's `Quiz` action, and confirm the
   saved attempt still appears.
