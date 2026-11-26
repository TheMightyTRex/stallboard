# Reviewing a submission

This page is for maintainers. A submission arrives as an issue made from the form, and the robot has commented with what passed. You decide whether to add the label `approved`, which opens a pull request. Read the plug-in's own files, not only the comment.

Never run anything from the submission on your own computer. Read it on GitHub.

## The checklist

1. **What it asks for against what it says it does.** Open the plug-in's `starboard-plugin.json`. For each permission, find the sentence in the description or the submitter's answer that needs it. A permission with no reason is a question to the submitter.

   High risk permissions (`jellyfin:key`, `reelix:key`, `usenet:servers`, `library:holding`) need a clear reason. A plug-in that reaches the internet should say what it sends and to whom. `network:lan` also lets a plug-in reach the internet.
2. **The licence.** It is a real licence. It is the same in the file and in the form. It lets Stallboard list the plug-in and link to it.
3. **The image is pinned by digest.** Each container's image is `name@sha256:...`. The image comes from the maker's own registry or repository, and the repository builds it (look for the workflow or Dockerfile). A digest the maker cannot explain is a reason to stop.
4. **The maker's repository.** It exists and matches the manifest's home page. The code is the code the image is built from, and the maker is who they say they are. For a first submission from someone new, check their history.
5. **No secrets.** No keys, tokens, passwords or private addresses in the manifest, its defaults, the repository or the image's files you can read.
6. **Its help and where to report problems.** The home page and `support_url` work. The plug-in has help a person can follow. A page "Report a problem with this plug-in" needs somewhere to go.
7. **The logo and words.** The logo has a description. The name and description say what it does, in plain words, and do not claim more than it does.
8. **The listing and snapshot in the pull request.** Read `listings/<id>.json` (who reviewed it, the category) and the snapshot. The Reviewed mark names you and the date, so only approve what you read.

## After you approve

The workflow opens a pull request with the checklist. Tick it, change `kind` if the category is wrong, and merge. Merging deploys the site. If something is wrong, close the pull request and say why on the issue.

## When a refresh pull request arrives

The daily refresh reads every listed plug-in's file again. Anything that **asks for more than before** is in bold: that needs the same review as a new listing. A new image digest needs step 3 again. If a plug-in's file no longer passes Starboard's check, its old snapshot stays, and the listing is left out of the site after 14 days.

## Taking a plug-in off

Delete its `listings/<id>.json` in a pull request and say why on the issue. Do it at once for anything harmful.

## The mark Starboard's own

A submitter cannot claim it. The checks refuse any maker name that contains the owner's name, and they ignore spaces, case and look-alike letters. The mark comes only from `"own": true` in a listing file. Never add `own` to a listing unless the plug-in is the owner's.

If a pull request from the approval workflow carries `own`, close it.

## Addresses must be a commit

A listing's manifest address must be `raw.githubusercontent.com/<owner>/<repo>/<40 hex commit>/...`, so the file you read is the file Starboard installs. The catalogue carries the file's SHA-256, and Starboard refuses a file that differs ("The file changed since the catalogue listed it, so Starboard did not use it"). A new version is a new submission with a new commit address. It can also be a pull request that changes the listing's address and snapshot after you read it.

## The first real run of the approval workflow

It could not be tested before the repository had labels and settings. Test it once, with a throwaway plug-in, before relying on it:

1. Labels exist (`tools/setup-labels.sh`) and Actions may create pull requests.
2. Open a submission with a plug-in file at a commit address. Within a minute the issue should have a comment "Checks on your plug-in" and the label `checks-passed` (or `checks-failed` with what to fix). The comment ends with a hidden line `stallboard-checks sha256=...`.
3. Add `approved` as a maintainer. Within a minute there should be a pull request that adds `listings/<id>.json` and `data/snapshots/<id>.json`, with "Closes #n" and the checklist. The reviewer named is you.
4. Add `approved` as someone without write access, or check the run log of a label added by a bot. Nothing is opened, the label is removed and a comment says why.
5. Edit the issue after approval and add the label again: it must refuse until the checks have run on the new text.
6. Close the test pull request without merging, and delete the branch.

Also check that the run logs show no secret and that the `open-pr` job is the only one with write access.
