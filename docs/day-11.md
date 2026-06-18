# Day 11 - Quiz Generation

## Goal

Turn an uploaded and parsed document into exam-style questions that can be saved,
loaded again, and reviewed in the browser.

## Flow

```text
Document chunks
  -> send selected chunk text to the local chat model
  -> ask for a strict JSON array of quiz questions
  -> validate the model response
  -> store questions in quiz_questions
  -> load and reveal answers in the frontend
```

## Database

The `quiz_questions` table stores reusable learning artifacts:

- `document_id`: which uploaded document the question belongs to
- `question_type`: `multiple_choice`, `short_answer`, or `true_false`
- `question`: the exam question text
- `choices`: JSON text for answer options
- `correct_answer`: the answer to reveal
- `explanation`: why the answer is correct

## API

```text
GET /documents/{document_id}/quiz
POST /documents/{document_id}/quiz/generate
```

The generate endpoint replaces old quiz questions for the same document. That
keeps repeated experiments simple while the app is still in development.

## Frontend

Each stored document now has two quiz actions:

- `Generate Quiz`: asks the backend to create and save new questions
- `Quiz`: loads existing questions without generating again

The quiz panel shows the question first. The answer and explanation stay hidden
until `Show Answer` is clicked.

## Key Idea

Flashcards test recall one fact at a time. Quiz questions are closer to exam
practice because they can include distractors, true/false checks, and short
explanations.
