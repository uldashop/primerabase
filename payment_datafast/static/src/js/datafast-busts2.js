odoo.define('payment_datafast.datafast', function (require) {
    "use strict";
    
    var ajax = require('web.ajax');
    var core = require('web.core');
    
    var qweb = core.qweb;
    var _t = core._t;
    
    if ($.blockUI) {
        // our message needs to appear above the modal dialog
        $.blockUI.defaults.baseZ = 2147483647; //same z-index as StripeCheckout
        $.blockUI.defaults.css.border = '0';
        $.blockUI.defaults.css["background-color"] = '';
        $.blockUI.defaults.overlayCSS["opacity"] = '0.9';
    }
    
    ajax.loadXML('/payment_datafast/static/src/xml/datafast_templates2.xml', qweb).then(function(){
        var _get_checkout_id = $('form[provider="datafast"]').find('input[name="checkout_id"]').val();
        var _mode=$('form[provider="datafast"]').find('input[name="mode"]').val();
        var url = "";
        if(_mode==='test'){
            url = "https://test.oppwa.com/v1/paymentWidgets.js?checkoutId=";
        }
        else
        {
            url = "https://oppwa.com/v1/paymentWidgets.js?checkoutId=";
        }
        showForm(qweb);
        $.ajaxSetup({cache:true});

        $.getScript(url+_get_checkout_id, function (data, textStatus, jqxhr) {
            //observer.observe(document.body, {childList: true});
            //_redirectToStripeCheckout($('form[provider="datafast"]'));
            $.unblockUI();
        })

    });
    
    require('web.dom_ready');
    if (!$('.o_payment_form').length) {
        return Promise.reject("DOM doesn't contain '.o_payment_form'");
    }
    
    /*var observer = new MutationObserver(function (mutations, observer) {
        for (var i = 0; i < mutations.length; ++i) {
            for (var j = 0; j < mutations[i].addedNodes.length; ++j) {
                if (mutations[i].addedNodes[j].tagName.toLowerCase() === "form" && mutations[i].addedNodes[j].getAttribute('provider') === 'datafast') {
                    _redirectToStripeCheckout($(mutations[i].addedNodes[j]));
                }
            }
        }
    });*/
    
    
    function showForm(qweb){

        console.log(window.location.origin);
        var wizard = $(qweb.render('datafast.placeholder',{'url': window.location.origin + '/payment/datafast/ressource' }));
        wizard.appendTo($('body')).modal({'keyboard': true, 'backdrop':'static'});
        if ($.blockUI) {
            $.unblockUI();
        }
        //$("#o_payment_form_pay").removeAttr('disabled');
         var button = $("#o_payment_form_pay");
            $(button).removeAttr('disabled');
            $(button).find("span.o_loader").remove();



    }
    function _redirectToStripeCheckout(providerForm) {
        // Open Checkout with further options
        if ($.blockUI) {
            var msg = _t("Just one more second, We are redirecting you to Datafast...");
            $.blockUI({
                'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
            });
        }
        
    
        var paymentForm = $('.o_payment_form');
        if (!paymentForm.find('i').length) {
            paymentForm.append('<i class="fa fa-spinner fa-spin"/>');
            paymentForm.attr('disabled',false);
        }
        paymentForm.addClass('paymentWidgets');
        
        var _getStripeInputValue = function (name) {
            return providerForm.find('input[name="' + name + '"]').val();
        };

        
    }
    
    });
    