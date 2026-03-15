document.addEventListener("DOMContentLoaded", function () {

    const navbar = document.querySelector(".navbar");
    const nav = document.querySelector("nav");

    if (!navbar || !nav) return;

    /* CREATE HAMBURGER */

    const burger = document.createElement("div");

    burger.innerHTML = "☰";

    /* FORCE STYLE (so CSS conflicts don't hide it) */

    burger.style.fontSize = "28px";
    burger.style.cursor = "pointer";
    burger.style.marginLeft = "auto";
    burger.style.padding = "5px 10px";
    burger.style.display = "none";

    /* ADD TO NAVBAR */

    navbar.appendChild(burger);

    /* MOBILE CHECK */

    function checkScreen(){

        if(window.innerWidth <= 768){

            burger.style.display = "block";

            nav.style.display = "none";

        }else{

            burger.style.display = "none";

            nav.style.display = "flex";

        }

    }

    checkScreen();

    window.addEventListener("resize", checkScreen);

    /* TOGGLE MENU */

    burger.addEventListener("click", function(){

        if(nav.style.display === "none"){

            nav.style.display = "flex";
            nav.style.flexDirection = "column";
            nav.style.position = "absolute";
            nav.style.right = "20px";
            nav.style.top = "65px";
            nav.style.background = "rgba(255,255,255,0.95)";
            nav.style.padding = "20px";
            nav.style.borderRadius = "10px";
            nav.style.boxShadow = "0 10px 30px rgba(0,0,0,0.2)";

        }else{

            nav.style.display = "none";

        }

    });

});