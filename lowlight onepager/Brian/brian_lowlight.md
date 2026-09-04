# Three constraints I did not replace

**Brian Lee (`brianlee0113`) · Columbia Market · September 2026**

I founded a company that builds apps for a living, and I keep several side
projects running, but this was my first time working with AI as a team rather
than on my own. I went in expecting a lot from it, and I came out having learned
a lot — mostly from what went wrong. The speed AI now brings can be an enormous
weapon, but this week left me sure it does not automatically translate into a
better output.

---

## 1 · We had no way to split work that is mostly prompting

***How I noticed:*** At kickoff, trying to assign tasks. This is a team
assignment, but the natural shape of the work turned out to be everyone watching
one laptop and one person's prompts. Three people reading a fourth person's chat
window is not a division of labour, and it was obvious within the first session.

***What I think went wrong:*** Before AI, the split was legible: frontend,
backend, design — each a surface someone owned. With an agent writing the code,
the unit of work is no longer a file or a layer, it is a prompt against a shared
repository, and two people prompting the same repository at once mostly produces
merge conflicts and duplicated intent. We had no structure for that, and I still
don't know what the right one is. It is the question I most want answered.

***What I did about it:*** We replaced the split with a sequence: one person
generates the skeleton, then the work divides. To keep that skeleton from being
slop everyone else inherits, I drew the UI/UX in Figma first — all five flows,
desktop and mobile — so we could confirm that what was on screen matched what we
had actually agreed before any code existed. That part worked; the disagreements
surfaced on the artboards instead of in the codebase. The division-of-labour
problem I only deferred.

## 2 · The agent led the product and we followed

***How I noticed:*** The early conversations — what the item is, which flows
matter — felt like ours. Once the skeleton landed, the codebase moved faster
than any of us could read it. The clearest symptom came at the end: the product
worked, and I still caught myself asking *is this actually done?* I could not
answer from memory, only by opening it and clicking through.

***What I think went wrong:*** A one-week deadline makes heavy AI dependence close
to unavoidable, but what I gave up was the checkpoint. On my own projects I set
a concrete target per day and do not advance until it is tested; that is what
produces visibility. Here there was no per-step acceptance criterion, so
"reviewed" quietly degraded into "it ran without errors."

***What I did about it:*** Partially, and late. I pulled the branch, brought up
the frontend and backend locally, and walked the flows myself instead of
trusting summaries; work landed through pull requests that were read before
merging. That recovered some ground. Next time I would require something
demoable each day and refuse to move on without it. There is a lot of talk now
about harness and loop engineering — letting the agent drive the cycle — and
after this week I am genuinely curious how well it holds up, because the failure
I hit is exactly the one that approach has to solve.

## 3 · It became an app-building project, not a Python project

***How I noticed:*** By looking at what we had actually shipped. The course is
Analytics in Python; the deliverable is a Next.js frontend on a FastAPI backend,
where most of the Python is plumbing — routing, ORM models, request handling —
rather than analysis.

***What I think went wrong:*** We decided what we wanted to build and fitted
Python to it afterwards. With an agent writing the code the language barrier
mostly disappears, so the stack stops being a constraint — and once it stops
being a constraint it also stops steering the design. The requirement never got
to shape the product.

***What I did about it:*** Kobe built the analysis side: user behaviour analysis
over the marketplace data and a dashboard on top of it, with the analytical work
kept in pandas in its own module rather than scattered through the API layer.
That gave the project a real analytics core instead of a chart bolted on at the
end, and it is the part of the repository that most clearly belongs to this
course. The ordering was still backwards. Starting from an analytics question
and building only the application needed to produce the data would have been the
honest version of this project.

---

All three are the same shape. AI removed a constraint, and the constraint had
been doing useful work — forcing us to divide the work, to move in verifiable
steps, and to stay inside the subject of the course. Removing friction is not
free. Whatever structure that friction was providing has to be rebuilt on
purpose, and we did not.
