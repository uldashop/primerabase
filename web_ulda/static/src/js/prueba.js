
const $productDetail = document.querySelector('#product_details')
const $btn_addToCart = $productDetail.querySelector('#add_to_cart')
const $seccion_variantes = $productDetail.querySelector('.js_add_cart_variants')
const $counter = $productDetail.querySelector('.te_product_quantity')
const $btn_buyNow = $productDetail.querySelector('#buy_now')

const $nuevoDiv = document.createElement('div')
$nuevoDiv.classList.add('nuevo-div')

$nuevoDiv.appendChild($counter)
$nuevoDiv.appendChild($btn_addToCart)
$nuevoDiv.appendChild($btn_buyNow)

$seccion_variantes.after($nuevoDiv)


//change icon breadcumb /shop
const $breadcrumb = document.querySelector('.te_product_breadcrumb ol.breadcrumb')
const $item_shop = $breadcrumb.querySelector('li a')
$item_shop.innerHTML = "<img src='/web_ulda/static/img/site/general/home.png'/>"

