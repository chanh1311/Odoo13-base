window.onload = () => {
    // (A) GET ALL IMAGES
    let all = document.getElementsByTagName("img");

    // (B) CLICK TO GO FULLSCREEN
    if (all.length > 0) {
        for (let i of all) {
            i.parentNode.classList.add("text-center");
            i.onclick = () => {
                i.classList.toggle('zoomed');
                // // (B1) EXIT FULLSCREEN
                // if (document.fullscreenElement != null || document.webkitFullscreenElement != null) {
                //   if (document.exitFullscreen) { document.exitFullscreen(); }
                //   else { document.webkitCancelFullScreen(); }
                // }
                //
                // // (B2) ENTER FULLSCREEN
                // else {
                //   if (i.requestFullscreen) { i.requestFullscreen(); }
                //   else { i.webkitRequestFullScreen(); }
                // }
            };
        }
    }

    // var vid = document.getElementsByTagName("video");
    //
    // // Attach a seeking event to the video element, and execute a function if a seek operation begins
    // if (vid.length > 0) {
    //     for (let i of vid) {
    //         i.addEventListener('seeking', function (event) {
    //             i.currentTime = (event.offsetX / i.offsetWidth) * i.duration;
    //         });
    //     }
    // }
};
