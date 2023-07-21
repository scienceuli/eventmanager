
var originalPrice = parseFloat(document.getElementById('totalprice').textContent);
var discountText = document.getElementById("discount-text");

function changePrice() {
    var checkBox = document.getElementById("id_vfll");
    var singlePriceElement = document.getElementById('price');
    var discountedSinglePriceElement = document.getElementById('discounted-price');
    var priceElement = document.getElementById('totalprice');
    var discountedPriceElement = document.getElementById('discounted-totalprice');
    

    if (checkBox.checked == true) {
        // hide the priceElement and singlePriceElement
        singlePriceElement.style.display = "none";
        priceElement.style.display = "none";
        // show the discounted prices and dicounted Text
        discountedPriceElement.style.display = "block";
        discountedSinglePriceElement.style.display = "block";
    } else {
        // show priceElement and singlePriceElement
        priceElement.style.display = "block";
        singlePriceElement.style.display = "block";
        // hide discounted prices and text
        discountedPriceElement.style.display = "none";
        discountedSinglePriceElement.style.display = "none";
    }

}
