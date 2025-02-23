
# Songle

Wordle but instead of guess the word you guess songs from your playlists.


## Setting up

Install dependencies, It is generally recommended you do this inside virtual environment but you do you.
```
-pip install requirements.txt 
```
Set up your environment using [spotify API](https://developer.spotify.com/dashboard) as following.
```
SPOTIFY_CLIENT_ID=[your client id]
SPOTIFY_CLIENT_SECRET=[your client secret]
SPOTIFY_REDIRECT_URL=http://localhost:5000/callback
```
Run
```
python app.py
```
## Note (IMPORTANT PLS READ)

- The program will saved your spotify access token and your tracks list **locally** in /saves so don't run this in public computer or delete your save after you're done. I do this to reduce the amount of request to spotify.
- The program is buggy since i don't think i do know what i'm doing
- **You need to be spotify premium user to run this** since non-premium user cannot request to run track from spotify's sdk
- If the program error you either (a) go back to home page (/home) or (b) remove your save file then re-login or (c) terminate then run the program again or all of them should fix it.
- Program is massively unoptimize so it'll take a while if you got gajillion songs in your playlist but hey its work
- You are **recommended to close any other spotify instance** while you run this
- You should **close tab** first then terminate program otherwise you might face the same [abomination](https://media.discordapp.net/attachments/540130478653702154/1343193200067739750/image.png?ex=67bc61a6&is=67bb1026&hm=353cba0d51c89b0eee85a29c4c466c2e60a05563bf5c848ecea3792901094e81&=&format=webp&quality=lossless&width=252&height=714) as me



## Known Bugs
 - Sometimes in the program will play the track *after* time limit is reach then continues until user press play again or the song end (i guess this is due to some api delay stuff but i cannot replicate it consistantly nor i can find a fix)
## Screenshots
Here's some choppy screenshot
![Yippee](https://media.discordapp.net/attachments/871295377834389524/1343234507175628842/image.png?ex=67bc881e&is=67bb369e&hm=6609cf139a90af7f85f4e7565b798fd8783e1ef49923d3d92719b1f7b102a8c8&=&format=webp&quality=lossless&width=762&height=905)

![Yippee](https://media.discordapp.net/attachments/871295377834389524/1343234593222037576/image.png?ex=67bc8833&is=67bb36b3&hm=53145668c83d51872a8903d27f1d4c44cd1581a9ed7c287ea3ba562d7a4ef1b6&=&format=webp&quality=lossless&width=707&height=905)

