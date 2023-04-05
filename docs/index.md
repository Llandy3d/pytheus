<p align="center">
  <img width="360px" src="/img/pytheus-logo.png" alt='pytheus'>
</p>
<p align="center">
    <em>playing with metrics</em>
</p>

# Introduction

pytheus is a modern python library for collecting [prometheus](https://prometheus.io/docs/introduction/overview/) metrics built with multiprocessing in mind.

Some of the features are:

  - multiple multiprocess support:
    - redis backend ✅
    - bring your own ✅
  - support for default labels value ✅
  - partial labels value (built in an incremental way) ✅
  - customizable registry support ✅
  - registry prefix support ✅

---
## Philosophy

Simply put is to let you work with metrics the way you want.

Be extremely flexible, allow for customization from the user for anything they might want to do without having to resort to hacks and most importantly offer the same api for single & multi process scenarios, the switch should be as easy as loading a different backend without having to change anything in the code.

- What you see is what you get.
- No differences between `singleprocess` & `multiprocess`, the only change is loading a different backend and everything will work out of the box.
- High flexibility with an high degree of `labels` control and customization.

---
## Requirements

- Python 3.10+
- redis >= 4.0.0 (**optional**: for multiprocessing)
