---
name: debug-rag-api
description: >-
  Use this skill to debug the Agentic RAG API. It parses the API log file to find any errors, warnings, and to trace end-to-end details for each request.
---

# Debug RAG API Skill

This skill guides you through debugging the Agentic RAG API by analyzing its log file.

## Steps to Execute

1. **Locate the Log File:**
   - The API writes logs to a file named `rag_api.log`, typically located in the `skills_demo` directory or the root directory, depending on where it was run.
   - First, find and open this log file using your tools (e.g. `view_file`).

2. **Extract Errors and Warnings:**
   - Read the contents of the log file.
   - Specifically look for log entries containing `ERROR` or `WARNING`.
   - Report any identified errors or warnings to the user, including the timestamp and context. If none are found, confirm that the API is running without errors.

3. **Trace End-to-End Requests:**
   - The log file tracks the lifecycle of each request. Key markers include:
     - `Received query request: <question>`
     - `[SEARCH] Vector Search: <query>`
     - `[USER QUERY]: <question>`
     - `[RAW RESPONSE]: <agent output>`
     - `Successfully processed query and returning response.`
   - Reconstruct the flow of each request by grouping the logs sequentially.
   - Present a clear summary of each request to the user, showing the input, the search terms used, and the final status.

4. **Summarize Findings:**
   - Provide an overall assessment of the API's health based on the logs.
