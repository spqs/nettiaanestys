/*jslint white: false, onevar: true, undef: true, newcap: true, nomen: true, regexp: true, plusplus: true, bitwise: true, browser: true, devel: true, maxerr: 50, indent: 4 */
/*global window: false, $: false, Modernizr: false */

/* Author:

 */
$(function() {
    if (!Modernizr.input.autofocus) {
        $('input[autofocus]').focus();
    }

    /* Build the data for the candidate search */
    var data = [];
    $('div.candidate h3').each(function(index) {
        // Give each candidate an id we can link to
        var $candidate = $(this);
        $candidate.attr({'id': 'candidate-' + index});
        data.push({
            'type': 'candidate',
            'label': $candidate.text(),
            'anchor': '#candidate-' + index});
    });

    /* Activate the candidate search */
    if (data.length > 0) {

        var label, form;

        label = $('<label></label>').html('Haku ');

        $('<input>', {
            'id': 'candidate-search',
            'name': 'search',
            'type': Modernizr.inputtypes.search ? 'search' : 'text'
        }).attr('placeholder', 'Hae nimellä tai numerolla').appendTo(label);

        form = $('<form></form>', {
            id: 'candidate-search-form',
            autocomplete: 'off'
        });
        label.appendTo(form);

        $('#search-wrapper').html(form);

        // Prevent default functionality for search form submit.
        $('#candidate-search').closest('form').submit(function (e) {
            if ($('.ui-autocomplete:visible').length === 0) {
                alert("Ei tuloksia haulle: " + $('#candidate-search').val());
            }
            e.preventDefault();
        });

        $('#candidate-search').autocomplete({
            source: data,
            select: function (e, ui) {
                var $item = $(ui.item.anchor),
                    $search = $('#candidate-search');

                $('.search-hit').removeClass('search-hit');
                $item.parent().addClass('search-hit');

                $.scrollTo(ui.item.anchor, {
                    duration: 500,
                    offset: {
                        left: 0,
                        top: - ($(window).height() || 0) / 2
                    }
                });

                // Clear the search box.
                setTimeout(function () {
                    $search.val('').trigger('blur');
                }, 1000);
            }
        });

    }

    // Add placeholder support for browsers that don't have it built in.
    if (!Modernizr.input.placeholder) {
        $('input[placeholder]').each(function () {
            var input = $(this),
                placeholder = input.attr('placeholder');

            // Add placeholder text to the value attr.
            input.addClass('placeholder-active').val(placeholder);

            input.focus(function () {
                // Remove placeholder text on focus.
                if (input.val() === placeholder) {
                    input.val('');
                }
                input.removeClass('placeholder-active');
            }).blur(function () {
                // Add placeholder text on blur if value attr is empty.
                if (!input.val()) {
                    input.addClass('placeholder-active');
                    input.val(placeholder);
                }
            });
        });
    }

    /* Create window close buttons */
    $('.exit')
        .live('click', function () {
            if (window.console) {
                console.log("Closing window");
            }
        })
        .replaceWith('<form><input type="button" class="exit" title="Poistu äänestyksestä" value="Poistu äänestyksestä" /></form>');
});
