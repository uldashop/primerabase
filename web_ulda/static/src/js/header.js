
const $header = document.querySelector('.te_header_style_2_main')
if($header){
    const $header_icon_wish = $header.querySelector('.te_wish_icon_head a')
    if($header_icon_wish){
        let $imagen_wish= document.createElement('img')
        $imagen_wish.setAttribute('src', '/web_ulda/static/img/site/header/heart.png')
        $header_icon_wish.appendChild($imagen_wish)
    
        let $icon_i_wish = $header_icon_wish.querySelector('i')
        $icon_i_wish.setAttribute('style', 'display:none!important;')
    }
    
    const $header_icon_cart = $header.querySelector('.te_cart_icon_head a')
    if($header_icon_cart){
        let $imagen_cart= document.createElement('img')
        $imagen_cart.setAttribute('src', '/web_ulda/static/img/site/header/shopping-cart.png')
        $header_icon_cart.appendChild($imagen_cart)
        let $icon_i_cart = $header_icon_cart.querySelector('i')
        $icon_i_cart.setAttribute('style', 'display:none!important;')
    
    }
    
    const $header_icon_user = $header.querySelector('.te_user_account_name')
    if($header_icon_user){
        let $imagen_user= document.createElement('img')
        $imagen_user.setAttribute('src', '/web_ulda/static/img/site/header/user-circle.png')
        $header_icon_user.appendChild($imagen_user)
    
        let $icon_i_user = $header_icon_user.querySelector('i')
        $icon_i_user.setAttribute('style', 'display:none!important;')
    }
}



