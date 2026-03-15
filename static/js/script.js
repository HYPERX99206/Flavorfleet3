
document.addEventListener("DOMContentLoaded", function(){

const cards=[...document.querySelectorAll(".restaurant-card")];
const total=document.getElementById("totalCount");
const visible=document.getElementById("visibleCount");

function updateCount(){
 let shown=cards.filter(c=>c.style.display!=="none").length;
 if(visible) visible.innerText=shown;
 if(total) total.innerText=cards.length;
}

window.searchRestaurants=function(){
 const input=document.getElementById("searchInput").value.toLowerCase();
 cards.forEach(c=>{
  const name=c.dataset.name.toLowerCase();
  c.style.display=name.includes(input)?"":"none";
 });
 updateCount();
}

window.sortRestaurants=function(){
 const container=document.getElementById("restaurantList");
 const filter=document.getElementById("sortFilter").value;
 let sorted=[...cards];

 if(filter==="az") sorted.sort((a,b)=>a.dataset.name.localeCompare(b.dataset.name));
 if(filter==="za") sorted.sort((a,b)=>b.dataset.name.localeCompare(a.dataset.name));
 if(filter==="rating") sorted.sort((a,b)=>parseFloat(b.dataset.rating)-parseFloat(a.dataset.rating));

 sorted.forEach(c=>container.appendChild(c));
}

window.toggleFilters=function(){
 const panel=document.getElementById("advancedFilters");
 if(panel) panel.classList.toggle("show");
}

window.updatePrice=function(){
 const v=document.getElementById("priceSlider").value;
 document.getElementById("priceValue").innerText=v;
}

window.updateRating=function(){
 const v=document.getElementById("ratingSlider").value;
 document.getElementById("ratingValue").innerText=v;
}

window.applyFilters=function(){

 const rating=parseFloat(document.getElementById("ratingSlider").value);
 const delivery=parseInt(document.getElementById("deliveryFilter").value||0);
 const price=parseInt(document.getElementById("priceSlider").value);

 const cuisines=[...document.querySelectorAll(".cuisine-tags input:checked")]
   .map(c=>c.value.toLowerCase());

 cards.forEach(card=>{
   let show=true;

   const cardRating=parseFloat(card.dataset.rating||0);
   const cardDelivery=parseInt(card.dataset.delivery||0);
   const cardPrice=parseInt(card.dataset.price||0);
   const cardCuisine=(card.dataset.cuisine||"").toLowerCase();

   if(cardRating<rating) show=false;
   if(delivery && cardDelivery>delivery) show=false;
   if(cardPrice>price) show=false;

   if(cuisines.length>0){
      const match=cuisines.some(c=>cardCuisine.includes(c));
      if(!match) show=false;
   }

   card.style.display=show?"":"none";
 });

 updateCount();
}

updateCount();

});
