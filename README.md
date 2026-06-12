# README

## My Agent
- just spin up more docker containers if you want more agents
- dedicated "gateway" container and "runner" container
- configuration is in a config file + .env ONLY, no flags, no memory-only configs
- linux native
- supports non-root podman ootb
- custom tool is easy
- need extra tools? spin up a new container! firecrawl, blah
- highly controllable, know what goes in, and comes out

## All agents
- custom tools are hard!

## Claude code CLI
- dislikes
  - confusing to configure

## Claude desktop
- likes
  - looks
  - easy configs
- dislike
  - did it reload?
  - does not support other providers
  - custom tools are HARD

## Hermes
- what I like
  - self hostable easily
  - the cli `hermes config xyz` just does it
- dislike
  - agent crap all over your config. Unmanagable w/o docker
  - docker permission hell
  - can't I host the gateway somewhere else and allow edits here?
  - does not allow multiple sessions at once
  - permission hell
  - no native web
  - confusing to configure
    - which configuration goes where again?
  - configuring and reloading. Did it reload yet???
  - web search and web extract are not natively supported

## Decisions:
- using python > go since we want immediate reload ability, and I don't want javascript