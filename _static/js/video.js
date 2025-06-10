document.addEventListener("DOMContentLoaded", function () {
    const videoSource = document.getElementById("video-source");
    const htmlElement = document.documentElement; 

    function updateVideoSource() {
        const theme = htmlElement.lastChild.getAttribute("data-md-color-scheme");
        if (theme === "slate") {
            videoSource.src = "_static/_videos/sequence_dark.mp4"; // Video for dark theme
        } else {
            videoSource.src = "_static/_videos/sequence.mp4"; // Video for light theme
        }
        videoSource.parentElement.load(); // Reload the video with the new source
    }

    // Initial check
    updateVideoSource();

    // Listen for theme changes
    const observer = new MutationObserver(updateVideoSource);
    observer.observe(htmlElement.lastChild, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
});