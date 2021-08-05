odoo.define('opa_ecomm_essentials.website_sale', function (require) {
  'use strict';
  var publicWidget = require("web.public.widget");

  publicWidget.registry.WebsiteSale = publicWidget.registry.WebsiteSale.extend({
    read_events: {
      'change select[name="state_id"]': "_onChangeState",
    },

    _changeState: function () {
      if (!$("#state_id").val()) {
        return;
      }
      this._rpc({
        route: "/shop/state_infos/" + $("#state_id").val(),
        params: {
          mode: "shipping",
        },
      }).then(function (data) {
        // populate cities and display
        var selectCities = $("select[name='city_id']");
        var inicio = $("<option>")
          .text("Seleccione su ciudad")
          .attr("value", "")
          // .attr("data-code", "");
        // dont reload city at first loading (done in qweb)
        if (
          selectCities.data("init") === 0 ||
          selectCities.find("option").length === 1
        ) {
          if (data.city_id.length) {
            selectCities.html("");
            selectCities.append(inicio);
            _.each(data.city_id, function (x) {
              var opt = $("<option>")
                .text(x[1])
                .attr("value", x[0])
                // .attr("data-code", x[2]);
              selectCities.append(opt);
            });
            selectCities.parent("div").show();
          } else {
            selectCities.val("").parent("div").hide();
          }
          selectCities.data("init", 0);
        } else {
          selectCities.data("init", 0);
        }
      });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeState: function (ev) {
      if (!this.$(".checkout_autoformat").length) {
        return;
      }
      this._changeState();
    },
  });
});
$(function(){
  var options = {
    url: function(phrase) {
      
      return "/shop/city/"+ phrase ;
    },
  
    getValue: "name",
    list: {
      
      maxNumberOfElements: 20,
      match: {
        enabled: true
      }
    }
  };
  $('#city').easyAutocomplete(options);
  $('.easy-autocomplete').css({'width': '100%'});
})
