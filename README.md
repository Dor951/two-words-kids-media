# Two Words Kids media

Public pin images for the Two Words Kids Etsy shop. Pinterest's bulk upload loads them from here by their raw URL, so keep file names stable:
`https://raw.githubusercontent.com/Dor951/two-words-kids-media/main/pins/<id>.png`

Source and build scripts live in the private shop repo (`tools/make_pins.py`, `tools/pinterest_bulk.py`).

## Instagram

`instagram/schedule.json` lists feed posts (`type: post`: JPEG, caption, alt text) and Reels (`type: reel`: MP4 in `instagram/reels/`, cover JPEG, caption), each with a date and UTC time. Reels are built by `tools/make_reels.py` in the shop repo. The `instagram-post` workflow runs daily and publishes the oldest due post, at most one per day, through the Instagram API. Posts with a `hold` field are skipped until the hold is removed. Published posts are logged in `instagram/posted.json`.
Secrets: `IG_ACCESS_TOKEN` (long-lived token, Instagram API with Instagram Login) and `IG_USER_ID`. Without them the workflow does nothing.
