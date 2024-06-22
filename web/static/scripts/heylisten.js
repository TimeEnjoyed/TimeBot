const eventS = new EventSource("/sse/redeems/heylisten");


eventS.addEventListener("hey_listen_redeem", (event) => {
    const audio = new Audio("/static/audio/heylisten.mp3");
    audio.play();
});