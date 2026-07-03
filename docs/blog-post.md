# Building a Tiny Agent Loop Without Hiding the Loop

My previous project, [care-loop](https://github.com/jaydeepbajwa/care-loop), used an LLM suggestion queue: free-text symptom notes go in, a structured recommendation comes out, and a human accepts or overrides it. That made the next project obvious. I wanted the smallest possible repo that showed I understand the loop behind an agent instead of outsourcing the interesting parts to a framework.

## What Broke

The first uncomfortable part was deciding what counted as a model failure. Invalid JSON is easy to wave away in a demo, but it is one of the common ways an agent fails in practice. So the loop treats bad JSON as a first-class event, appends a repair instruction, and lets the model try again.

Tool errors had the same shape. A blocked write, an unknown tool, and a failing test command are not all the same thing. Failing tests are useful observations. A blocked write is a safety decision. An unknown tool is a schema mismatch. Splitting those cases made the code less magical and easier to explain.

## What I Would Redo

The next version would add trace persistence: each model response, tool call, and observation should be saved as a replayable run. That would make debugging easier and would also set up the eval harness I want to build next — replayable traces are exactly what you score.

I would also add a summarizer once the message list grows past a threshold. The current version is honest about its limit: it accumulates context until `--max-steps` ends the run.

## The Useful Lesson

The agent is not the API call. The agent is the contract around the API call: what the model is allowed to do, how tools report reality back, and what happens when the model is wrong. Keeping that contract small made the project easier to test and easier to defend in an interview.

