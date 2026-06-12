# README

## My Agent
- just spin up more docker containers if you want more agents
- dedicated "gateway" container and "runner" container
- configuration is in a config file + .env ONLY, no flags, no memory-only configs
- linux native
- supports non-root podman ootb

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
