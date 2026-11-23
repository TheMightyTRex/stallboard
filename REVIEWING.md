# Reviewing a submission

For maintainers. A submission arrives as an issue made from the form. The robot has commented with what passed. You decide whether to add the label `approved`, which opens a pull request. Read the plug-in's own files, not only the comment.

Never run anything from the submission on your own computer. Read it on GitHub.

## The checklist

1. **What it asks for against what it says it does.** Open the plug-in's `starboard-plugin.json`. For each permission, find the sentence in the description or the submitter's answer that needs it. A permission with no reason is a question to the submitter. High risk permissions (`jellyfin:key`, `reelix:key`, `usenet:servers`, `library:holding`) need a clear reason. A plug-in that reaches the internet (`network:lan` also lets it reach the internet) should say what it sends and to whom.
2. **The licence.** It is a real licence, it is the same in the file and in the form, and it lets Stallboard list the plug-in and link to it.
3. **The image is pinned by digest.** Each container's image is `name@sha256:...`. The image comes from the maker's own registry or repository, and the repository builds it (look for the workflow or Dockerfile). A digest the maker cannot explain is a reason to stop.
4. **The maker's repository.** It exists, it matches the manifest's home page, the code is the code the image is built from, and the maker is who they say they are. For a first submission from someone new, look at their history.
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
