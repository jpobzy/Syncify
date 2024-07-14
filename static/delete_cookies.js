console.log('index2.js loaded')

document.getElementById("deleteCookiesBtn").addEventListener("click", function() {
    
    var cookies = document.cookie.split(";");

    // Loop through each cookie and delete it
    cookies.forEach(function(cookie) {
        var cookieParts = cookie.split("=");
        var cookieName = cookieParts[0].trim();
        document.cookie = cookieName + "=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    });

    localStorage.clear();
    sessionStorage.clear();

    alert("Cookies have been deleted.");
});
