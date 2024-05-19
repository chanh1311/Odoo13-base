odoo.define("lk_base.advanced_search", function(require) {
    "use strict";

	var time = require('web.time');
	var core = require('web.core');
    var ListRenderer = require('web.ListRenderer');
    var Domain = require('web.Domain');
    var QWeb = core.qweb;
    var _t = core._t;
    var _lt = core._lt;

    ListRenderer.include({
    	init: function(parent, state, params) {
			this._super.apply(this, arguments);
			this.field_data = [];
			this.array = {};
		},

		_processColumns: function (columnInvisibleFields) {
			this._super.apply(this, arguments);
			this.prepare_field_value();
		},

		prepare_field_value: function(){
			var self = this;
			_.each(this.state.fieldsInfo['list'], function (field_info) {
				var field = self.state.fields[field_info.name];
				self.field_data.push({
					'name': field_info.name,
					'string': field.string,
					'widget': field_info.widget,
					'type': field.type,
					'selection': field.selection,
					'relation': field.relation,
					'invisible': (_.some(self.columns, function(c) { return c.attrs.name === field_info.name; })) ? '1' : '0',
				})
			})
		},

		// load_search_row: async function
		prepare_many2one_value: async function(field_lst){
			var self = this;
			var filter = [];
			for (var field of field_lst){
				var domain = [];
				if (field['relation'] === 'res.partner'){
					domain.push(['is_user', '=', false]);
				}
				await new Model(field['relation']).query(['id', 'display_name'])
            	.filter(domain)
               	.all().then(function (result) {
                    if (result) {
                    	self.array[field['name']] = [];
						for (var line of result){
							self.array[field['name']].push([line['id'], line['display_name']]);
                        }
                    }
                });
       	 	}
    	},

		load_search_row: function(thead){
			var self = this;
			var l10n = _t.database.parameters;
			var datepickers_options = {
			};
            var sky_fields = [];
            var field_lst = [];
//            for (var value of this.columns){
//                 { //  && value.widget !== 'handle' && value.type !== 'integer' && value.type !== 'float' && value.widget !== 'disable_search' && value.invisible !== '1'
//                    if (typeof value.selection === 'undefined') {
//                        if (value.type === 'many2one') {
//                            field_lst.push({'relation': value.relation, 'name': value.name});
//                        }
//                    }
//            }
//            await self.prepare_many2one_value(self.model, field_lst);
            for (var c of self.columns){
            	var value = _.filter(self.field_data, function (f) {return f.name === c.attrs.name; })[0];
                // && value.widget !== 'handle' && value.type !== 'integer' && value.type !== 'float' && value.widget !== 'disable_search' && value.invisible !== '1'
                if (value){
					var value_type = value.type;
					if (value.type === 'many2one' || value.type === 'many2one'){
						value_type = "char";
					}
					if (typeof value.selection === 'undefined') {
	//                        if (value.type === 'many2one') {
	//							var field_data = self.array[value.name];
	//                            if (value.widget === 'search_many2many'){
	//                                sky_fields.push([value.name, value.string, "many2many", field_data, value.widget]);
	//                            }else {
	//                                sky_fields.push([value.name, value.string, value.type, field_data, value.widget]);
	//                            }
	//                        } else {
							sky_fields.push([value.name, value.string, value_type, value.selection, value.widget]);
	//                        }
					} else {
						sky_fields.push([value.name, value.string, value_type, value.selection, value.widget]);
					}
				}else{
					// in case of button
					sky_fields.push(["button", "button", "button", "button", "disable_search"]);
				}
            }
            if (sky_fields.length > 0) {
                self.$search_range = $(QWeb.render('SearchRow', {'sky_fields': sky_fields, 'widget': self}));
                self.$search_range.find('.start_date').datepicker(datepickers_options);
                self.$search_range.find('.end_date').datepicker(datepickers_options);
                self.$search_range.find('.many2one_field').select2({allowClear: true, dropdownCssClass: 'bigdrop'});
                self.$search_range.find('.many2many_field').select2({width: '110px', dropdownCssClass: 'bigdrop'});
                self.$search_range.find('input').on('keydown', function (ev) {
					ev.stopPropagation();
					if (ev.which === 13) {
						self.tgl_search();
					}
				});
                self.$search_range.find('#submit_search').on('click', function() {
                    self.tgl_search();
                });
//                self.$search_range.find('.search_field').on('change', function() {
//                    self.tgl_search();
//                    return false;
//                });
//                self.$search_range.find('.selection_field').on('change', function() {
//                    self.tgl_search();
//                    return false;
//                });
//                self.$search_range.find('.many2one_field').on('change', function() {
//                    self.tgl_search();
//                    return false;
//                });
//                self.$search_range.find('.many2many_field').on('change', function() {
//                    self.tgl_search();
//                    return false;
//                });
//                self.$search_range.find('.start_date').keypress(function (e) {
//                    self.tgl_search();
//                    return false;
//                });
//                self.$search_range.find('.end_date').keypress(function (e) {
//                    self.tgl_search();
//                    return false;
//                });
                if ($('#bullseye').length > 0) {
                    $('#bullseye div:last-child').remove();
                }
                // not working
//                if (self.field_values){
//					for (var item of self.field_values){
//						if(item.type === 'many2many_field'){
//							// recalculate selected option many2many
//							var arr = [];
//							_.each($('#bullseye #'+item.name).val(item.value).select2('data'), function(item) {
//								arr.push(item.id)
//							});
//							arr.push(item.value);
//							$('#bullseye #' + item.name).select2("val", arr);
//						} else if (item.type === 'many2one_field'){
//							if (item.value !== "") {
//								$('#bullseye #' + item.name).select2("val", item.value);
//							}else{
//								$('#bullseye #' + item.name).select2("val", "");
//							}
//						}else{
//							$('#bullseye #'+item.name).val(item.value);
//						}
//					}
//				}
                self.$search_range.appendTo(thead);
            }
		},

		tgl_search: function() {
			var self = this;
			var domain = [];
			var filter_lst = [];
			this.field_values = [];
			if (self.$search_range) {
				var l10n = _t.database.parameters;
				var search_fields = self.$search_range.find('.search_field');
				var start_date = self.$search_range.find('.start_date');
				var end_date = self.$search_range.find('.end_date');
				var selection_fields = self.$search_range.find('.selection_field');
				var many2one_fields = self.$search_range.find('.many2one_field');
				var many2many_field = self.$search_range.find('.many2many_field');
				_.each(search_fields, function(item){
					var input_field = item.name, input_value = item.value;
					if (input_value) {
						domain.push([input_field, 'ilike', input_value]);
						filter_lst.push(`${$(item).attr('placeholder')} like ${input_value}`);
//						self.field_values.push({
//							'name': input_field,
//							'value': input_value,
//							'type': 'search',
//						});
					}
				});
				_.each(start_date, function(item){
					var input_field = item.name, input_value = item.value;
					if (input_value) {
						input_value = moment(moment(item.value, time.strftime_to_moment_format(l10n.date_format))).format('YYYY-MM-DD');
						domain.push([input_field,'>=', input_value]);
						filter_lst.push(`${$(item).attr('placeholder')} >= ${input_value}`);
//						self.field_values.push({
//							'name': input_field,
//							'value': input_value,
//							'type': 'date',
//						});
					}
				});
				_.each(end_date, function(item){
					var input_field = item.name, input_value = item.value;
					if (input_value) {
						input_value = moment(moment(item.value, time.strftime_to_moment_format(l10n.date_format))).format('YYYY-MM-DD');
						domain.push([input_field,'<=', input_value]);
						filter_lst.push(`${$(item).attr('placeholder')} <= ${input_value}`);
//						self.field_values.push({
//							'name': input_field,
//							'value': input_value,
//							'type': 'date',
//						});
					}
				});
				_.each(selection_fields, function(item){
					var input_field = item.name, input_value = item.value;
					if (input_value) {
						domain.push([input_field, 'ilike', input_value]);
						filter_lst.push(`${$(item).attr('placeholder')} like ${input_value}`);
//						self.field_values.push({
//							'name': input_field,
//							'value': input_value,
//							'type': 'select',
//						});
					}
				});
				_.each(many2one_fields, function(item){
					var selected_data = $('#bullseye select.many2one_field#'+item.id).select2('data');
					if (selected_data !== null){
						var input_field = item.name, input_value = selected_data.id;
						if (input_value) {
							domain.push([input_field, '=', parseInt(input_value)]);
							filter_lst.push(`${$(item).attr('placeholder')} = ${input_value}`);
//							self.field_values.push({
//								'name': input_field,
//								'value': input_value,
//								'type': 'many2one_field',
//							});
						}
					}
				});
				_.each(many2many_field, function(item){
					var new_domain = [];
					_.each($('#bullseye select.many2many_field#'+item.id).select2('data'), function(data) {
						var input_field = item.name, input_value = data.id, is_exists = false;
						if (input_value) {
//							self.field_values.push({
//								'name': input_field,
//								'value': input_value,
//								'type': 'many2many_field',
//							});
							if (domain.length > 0){
								domain.forEach(function(field_domain){
									if (field_domain[0] === item.name){
										new_domain.push(parseInt(input_value));
										domain.splice(domain.indexOf(field_domain), 1);
										is_exists = true;
									}
								});
							}
							if (!is_exists){
								new_domain.push(parseInt(input_value));
								domain.push([input_field, '=', parseInt(input_value)]);
								filter_lst.push(`${$(item).attr('placeholder')} = ${input_value}`);
							}else{
								domain.push([input_field, 'in', new_domain.map(Number)]);
								filter_lst.push(`${$(item).attr('placeholder')} in ${new_domain.map(Number)}`);
							}
						}
					});
				});
			}
			this.do_search(domain, filter_lst);
		},

		do_search: function(domain, filter_lst) {
			var searchController = this.getParent()._controlPanel;
//			var current_search = searchController.model.getQuery();
//			current_search.domain = domain;
//			searchController.trigger_up('search', current_search);
//			var state = searchController.model.get();
//        	searchController.renderer.updateState(state);
			var filters = [];
			for (var i=0; i < domain.length; i++) {
				filters.push({
					type: 'filter',
					description: _.str.sprintf(filter_lst[i]),
					domain: Domain.prototype.arrayToString(domain),
				});
			}
			searchController.trigger_up('new_filters', {filters: filters});
		},

		_renderHeader: function () {
			var $thead = this._super.apply(this, arguments);
			$thead.attr('id', 'bullseye');
			// editable list cause error
			if (!this.editable && !this.creates && this.$el.hasClass('advanced_search')) {
				this.load_search_row($thead);
			}
			return $thead;
		},

		// hide nocontent-helper to always display advanced search
		_hasContent: function () {
			return true;
		},

		// fix wrong width of column
		_squeezeTable: function () {
			const table = this.el.getElementsByTagName('table')[0];
			// Toggle a className used to remove style that could interfer with the ideal width
			// computation algorithm (e.g. prevent text fields from being wrapped during the
			// computation, to prevent them from being completely crushed)
			table.classList.add('o_list_computing_widths');
			const thead = table.getElementsByTagName('thead')[0];

			const tr = thead.getElementsByTagName('tr')[0];
			const thElements = [...tr.querySelectorAll('th')];

			const columnWidths = thElements.map(th => th.offsetWidth);
			const getWidth = th => columnWidths[thElements.indexOf(th)] || 0;
			const getTotalWidth = () => thElements.reduce((tot, th, i) => tot + columnWidths[i], 0);
			const shrinkColumns = (columns, width) => {
				let thresholdReached = false;
				columns.forEach(th => {
					const index = thElements.indexOf(th);
					let maxWidth = columnWidths[index] - Math.ceil(width / columns.length);
					if (maxWidth < 92) { // prevent the columns from shrinking under 92px (~ date field)
						maxWidth = 92;
						thresholdReached = true;
					}
					th.style.maxWidth = `${maxWidth}px`;
					columnWidths[index] = maxWidth;
				});
				return thresholdReached;
			};
			// Sort columns, largest first
			const sortedThs = [...thead.getElementsByTagName('th')]
				.sort((a, b) => getWidth(b) - getWidth(a));
			const allowedWidth = table.parentNode.offsetWidth;
			let totalWidth = getTotalWidth();
			let stop = false;
			let index = 0;
			while (totalWidth > allowedWidth && !stop) {
				// Find the largest columns
				index++;
				const largests = sortedThs.slice(0, index);
				while (getWidth(largests[0]) === getWidth(sortedThs[index])) {
					largests.push(sortedThs[index]);
					index++;
				}
				// Compute the number of px to remove from the largest columns
				const nextLargest = sortedThs[index]; // largest column when omitting those in largests
				const totalToRemove = totalWidth - allowedWidth;
				const canRemove = (getWidth(largests[0]) - getWidth(nextLargest)) * largests.length;
				// Shrink the largests columns
				stop = shrinkColumns(largests, Math.min(totalToRemove, canRemove));
				totalWidth = getTotalWidth();
			}
			// We are no longer computing widths, so restore the normal style
			table.classList.remove('o_list_computing_widths');
			return columnWidths;
		},
    });
});
