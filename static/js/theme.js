
function toggleTheme(){

const body=document.body
body.classList.toggle("dark-mode")

localStorage.setItem(
"theme",
body.classList.contains("dark-mode") ? "dark" : "light"
)

}

document.addEventListener("DOMContentLoaded",function(){

if(localStorage.getItem("theme")==="dark"){
document.body.classList.add("dark-mode")
}

})