# Changelog

## [0.2.1](https://github.com/mxmehl/outlook-caldav-sync/compare/v0.2.0...v0.2.1) (2026-07-15)


### ⚙️ Chores

* add license information in pyproject ([754a3c1](https://github.com/mxmehl/outlook-caldav-sync/commit/754a3c1b173fd9dd460be5a80bdbad948958a33a))
* add license-files, repository URL, and changelog URL to pyproject.toml ([#10](https://github.com/mxmehl/outlook-caldav-sync/issues/10)) ([64b3ef1](https://github.com/mxmehl/outlook-caldav-sync/commit/64b3ef14bde26417c8240e109e0c74ae4f6155dc))

## [0.2.0](https://github.com/mxmehl/outlook-caldav-sync/compare/v0.1.0...v0.2.0) (2026-07-14)


### 🚀 New Features

* add argparse to be more flexible ([79e0be6](https://github.com/mxmehl/outlook-caldav-sync/commit/79e0be6b75ce31cb8219fac09becd92547faa066))
* add config to anonymize email addresses of attendees/organizers ([dc4fddd](https://github.com/mxmehl/outlook-caldav-sync/commit/dc4fdddf50b2cbd49ebe8168c5bb0fc43b7f39d5))
* add deletion step, some minor improvements ([d69e01e](https://github.com/mxmehl/outlook-caldav-sync/commit/d69e01ec494c4ee96eec90135be5092a2734eaca))
* add dry run mode ([2f6e00c](https://github.com/mxmehl/outlook-caldav-sync/commit/2f6e00cfe9a3fc939ddbcb2664fcfcd953a72716))
* add force flag to enforce sync ([6b4329e](https://github.com/mxmehl/outlook-caldav-sync/commit/6b4329e73d695a6dd029ff8302f7986f1c82e633))
* add ignored_categories ([147d59d](https://github.com/mxmehl/outlook-caldav-sync/commit/147d59d58b57cacda12aef7979239f872353764e))
* add organizers and attendees to ical events ([f4c0500](https://github.com/mxmehl/outlook-caldav-sync/commit/f4c05008da568b75d3a8a53eb21c49c91a3567e9))
* allow to add no-sync subject by regex ([169bd43](https://github.com/mxmehl/outlook-caldav-sync/commit/169bd43202c0a1f112260da89784abde4e7a5f28))
* allow to exclude events based on their showAs value ([d403722](https://github.com/mxmehl/outlook-caldav-sync/commit/d40372298107be7525d961fb4986908fc83661bc))
* explicitly delete no-sync events ([e0be786](https://github.com/mxmehl/outlook-caldav-sync/commit/e0be786d8d608ac87dc714e39bd1e70c3eefcb75))
* support making all events in calendar private ([2dd4855](https://github.com/mxmehl/outlook-caldav-sync/commit/2dd485512c8dc60c290b74815813d491a3ee946b))


### 🔥 Bug Fixes

* **deps:** update dependency caldav to v3 ([#6](https://github.com/mxmehl/outlook-caldav-sync/issues/6)) ([4c40ec4](https://github.com/mxmehl/outlook-caldav-sync/commit/4c40ec4a4e1836df9ee354c988afe4f14dfa1a00))
* **deps:** update dependency icalendar to v7 ([#7](https://github.com/mxmehl/outlook-caldav-sync/issues/7)) ([c21635d](https://github.com/mxmehl/outlook-caldav-sync/commit/c21635d51a8fea4e474fd10bdac7728ffb5db331))
* improve config, timezones ([e663bdc](https://github.com/mxmehl/outlook-caldav-sync/commit/e663bdcff7af7b6fe1a2dfc9249efb531802e373))


### 🧪 Automated Testing

* create tests ([c9a280d](https://github.com/mxmehl/outlook-caldav-sync/commit/c9a280d76e314a245c9b36062f9675d2fb3a19eb))


### 🛠️ Build System

* switch to uv/ruff/ty, use GH Workflow, add README ([a590783](https://github.com/mxmehl/outlook-caldav-sync/commit/a590783cce2fdcb10530922d1e02109af5733353))


### 📦 CI Improvements

* setup release-please ([2bd0955](https://github.com/mxmehl/outlook-caldav-sync/commit/2bd0955c31efe7cd0996cc70a86b6f593f574a28))


### ⚙️ Chores

* bump all dependencies ([ecf0f2b](https://github.com/mxmehl/outlook-caldav-sync/commit/ecf0f2b44bf5b2c45b44e64f103a3c61bac6dbdd))
* **deps:** lock file maintenance ([#8](https://github.com/mxmehl/outlook-caldav-sync/issues/8)) ([0979178](https://github.com/mxmehl/outlook-caldav-sync/commit/09791787e002450b0f52362bcb60050b1cfd584f))
* **deps:** update actions/checkout action to v7 ([db00e70](https://github.com/mxmehl/outlook-caldav-sync/commit/db00e70220fd1d15f3e86e6c471f134813d026e5))
* **deps:** update actions/checkout action to v7 ([29d2448](https://github.com/mxmehl/outlook-caldav-sync/commit/29d244804e4c8b4dc823204daadaa75845e0d9a4))
* **deps:** update dependency pytest to v9 ([#5](https://github.com/mxmehl/outlook-caldav-sync/issues/5)) ([19e1497](https://github.com/mxmehl/outlook-caldav-sync/commit/19e14976b94d6f37013951fb44b2675dd774c7b7))
* **deps:** update github actions group ([#2](https://github.com/mxmehl/outlook-caldav-sync/issues/2)) ([10447d0](https://github.com/mxmehl/outlook-caldav-sync/commit/10447d08de47ae234d6a6a22cc73413552cca9fb))
* do not sync event description and url ([abc2751](https://github.com/mxmehl/outlook-caldav-sync/commit/abc2751584bf2e44133927d87843353e3d3a56b8))
* fix typing for new CalDAV version ([481baf3](https://github.com/mxmehl/outlook-caldav-sync/commit/481baf33a856ccd2f09541dc4662d9809441ac28))
* improve information output ([15a418b](https://github.com/mxmehl/outlook-caldav-sync/commit/15a418b58bf974fb652c66883ba7961c4176b8f4))
* rewrite to local ICS handling, but ICS download times out ([a46b447](https://github.com/mxmehl/outlook-caldav-sync/commit/a46b4477bc6c2592ce1b1adc3fa528ac9aa23d48))
* rewrite using search(), but timeout still is an issue. Also, if the local JSON file has more events than search(), it always recreates them ([77928a9](https://github.com/mxmehl/outlook-caldav-sync/commit/77928a967ba15b96a85e15248266fc4522d0030a))
* separating, typing, encoding fixes ([e2eba23](https://github.com/mxmehl/outlook-caldav-sync/commit/e2eba236aa1549399622f2c16327b726590b3005))
* setup renovate ([a7a77f4](https://github.com/mxmehl/outlook-caldav-sync/commit/a7a77f409fdec429b5b6a37cf923a9a5a4a70b21))
