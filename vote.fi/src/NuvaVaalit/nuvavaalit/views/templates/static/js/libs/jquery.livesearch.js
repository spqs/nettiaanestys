jQuery.fn.liveUpdate = function(list){
	list = jQuery(list);

	if ( list.length ) {
		var rows = list.find('li.candidate > a'),
			cache = rows.map(function(){
				return this.innerHTML.toLowerCase();
			});
			
		this
			.keyup(filter).keyup()
			.parents('form').submit(function(){
				return false;
			});
	}
		
	return this;
		
	function filter(){
		var term = jQuery.trim( jQuery(this).val().toLowerCase() ), scores = [];
		rows.removeClass('search-hit');
		
		if ( term ) {

			cache.each(function(i){
				var score = this.score(term);
				if (score > 0) { scores.push([score, i]); }
			});

			jQuery.each(scores.sort(function(a, b){return b[0] - a[0];}), function(){
				jQuery(rows[ this[1] ]).addClass('search-hit');
			});
		}
	}
};
