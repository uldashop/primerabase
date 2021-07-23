//remove text warranty 30 days in product details
const $textMuted = document.querySelector('#product_details .text-muted')
if($textMuted){
    document.querySelector('#product_details').removeChild($textMuted)
}


//change icon breadcumb /shop (ulda)
const $breadcrumb = document.querySelector('.te_product_breadcrumb ol.breadcrumb')
const $item_shop = $breadcrumb.querySelector('li a')
$item_shop.innerHTML = "<img src='/web_ulda/static/img/site/general/home.png'/>"

/*
acomodar elementos de product details (ulda)
*/
const $productDetails = document.querySelector('#product_details')


//move tag product details
const $tag= $productDetails.querySelector('.te_prod_label')
if($tag){
    $productDetails.insertAdjacentElement('afterbegin', $tag) 
}


const $seccion_variantes = $productDetails.querySelector('.js_add_cart_variants')
const $counter = $productDetails.querySelector('.te_product_quantity')
const $btn_addToCart = $productDetails.querySelector('#add_to_cart')
const $btn_buyNow = $productDetails.querySelector('#buy_now')
const $nuevoDiv = document.createElement('div')
$nuevoDiv.classList.add('nuevo-div')
$nuevoDiv.appendChild($counter)
$nuevoDiv.appendChild($btn_addToCart)
$nuevoDiv.appendChild($btn_buyNow)
$seccion_variantes.after($nuevoDiv)


//alternative products title
const $alternativeProductsTitle = document.querySelector('#myCarousel_alt_prod .te_product_alt_h3')
if($alternativeProductsTitle){
    const newTitleAlternativeProducts=document.createElement('span')
    newTitleAlternativeProducts.innerHTML =`
    <section data-name="Title style 2" class="title_ulda">
        
            <div class="row s_nb_column_fixed">
                <div class="col-lg-12 te_title_2 pt32 pb32">
                    <div class="te_title_sub_div">
                    <h4 class=" te_s_title_default te_title_style2 o_default_snippet_text mb-0 pb-0">
                        OTROS RECOMENDADOS
                    </h4>
                    </div>
                </div>
            </div>
        
    </section>`
    document.querySelector('#myCarousel_alt_prod').insertAdjacentElement('afterbegin', newTitleAlternativeProducts) 
    $alternativeProductsTitle.classList.add('d-none')
}