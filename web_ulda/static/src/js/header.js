
const $header = document.querySelector('.te_header_style_2_main')

const $header_icon_wish = $header.querySelector('.te_wish_icon_head a')
const $header_icon_cart = $header.querySelector('.te_cart_icon_head a')
const $header_icon_user = $header.querySelector('.te_user_account_name')

const $imagen_wish= document.createElement('img')
const $imagen_cart= document.createElement('img')
const $imagen_user= document.createElement('img')

$imagen_wish.setAttribute('src', '/web_ulda/static/img/site/header/heart.png')
$imagen_cart.setAttribute('src', '/web_ulda/static/img/site/header/shopping-cart.png')
$imagen_user.setAttribute('src', '/web_ulda/static/img/site/header/user-circle.png')

$header_icon_wish.appendChild($imagen_wish)
$header_icon_cart.appendChild($imagen_cart)
$header_icon_user.appendChild($imagen_user)

const icon_i_wish = $header_icon_wish.querySelector('i')
const icon_i_cart = $header_icon_cart.querySelector('i')
const icon_i_user = $header_icon_user.querySelector('i')

icon_i_wish.setAttribute('style', 'display:none!important;')
icon_i_cart.setAttribute('style', 'display:none!important;')
icon_i_user.setAttribute('style', 'display:none!important;')


