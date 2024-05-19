odoo.define("lk_base.basic_fields", function(require) {
    "use strict";

    const core = require("web.core");
    const framework = require('web.framework');
    const utils = require('web.utils');
    const basic_fields = require("web.basic_fields");
    const view_dialogs = require("web.view_dialogs");
    const Domain = require("web.Domain");
    const DomainSelector = require("web.DomainSelector");
    const ModelFieldSelector = require("web.ModelFieldSelector");
    const field_utils = require ("web.field_utils");
    var relationalFields = require('web.relational_fields');
    var registry = require('web.field_registry');
    var _lt = core._lt;
    const _t = core._t;
    var Dialog = require('web.Dialog');
    var dialogs = require('web.view_dialogs');
    var modelFieldsCache = {
		cache: {},
		cacheDefs: {},
	};

	function sortFields(fields, model, order) {
		var array = _.chain(fields)
			.pairs()
			.sortBy(function (p) { return p[1].string; });
		if (order !== 'string') {
			array = array.sortBy(function (p) {return p[1][order]; });
		}
		return array.map(function (p) {
				return _.extend({
					name: p[0],
					model: model,
				}, p[1]);
			}).value();
	}

	// add attribute to limit display field in popup, **need add field in search view too
    DomainSelector.include({
		init: function (parent, model, domain, options) {
			this._super.apply(this, arguments);
			if (parent.nodeOptions.hasOwnProperty('limit_field') && _.isArray(parent.nodeOptions.limit_field)) {
				var node_field = parent.nodeOptions.limit_field;
				if (!node_field.includes("id")){
					node_field.push("id");
				}
				this.options.limit_field = node_field;
			}
		},

		// fix error when edit record, system not display limit field
		willStart: function () {
			var res = this._super.apply(this, arguments);
			if (this.fieldSelector && this.options.limit_field){
				this.fieldSelector.options.limit_field = this.options.limit_field;
			}
			return res;
		},

		start: function () {
			var self = this;
			var def = 1;
			if (this.options.hasOwnProperty('limit_field')){
				def = this._rpc({
					model: this.model,
					method: 'fields_get',
					args: [
						this.options.limit_field,
						["store", "searchable", "type", "string", "relation", "selection", "related"]
					],
					context: this.getSession().user_context,
				}).then(function (limit_fields) {
					self.options.fields = limit_fields;
				});
			}
			// fix error when edit record, system not display limit field
			if (this.fieldSelector && this.options.limit_field){
				this.fieldSelector.options.limit_field = this.options.limit_field;
			}
			return Promise.all([def, this._super.apply(this, arguments)]);
		},

		// fix odoo error, why change because not dealing with change field from char to integer
		_addFlattenedChildren: function (domain) {
			this._super.apply(this, arguments);
			if (domain.length == 1){
				var last_node = this.children.slice(-1)[0];
				if (last_node){
					var chain = domain[0][0];
					var value = domain[0][2];
					if (this.options.hasOwnProperty('fields') && this.options.fields.hasOwnProperty(chain)){
						var selectedField = this.options.fields[chain];
						try {
							value = field_utils.parse[selectedField.type](String(value), selectedField);
						} catch (err) {
							if (selectedField.type === "integer" || selectedField.type === "float" || selectedField.type === "monetary") {
								last_node.value = 1;
							}
						}
					}
				}
			}
		},
    });

    // display limit field (can use field related in main model) in widget domain, if use field relation system only display id and name.
    ModelFieldSelector.include({
    	_getModelFieldsFromCache: function (model, filters) {
			var self = this;
			var def = modelFieldsCache.cacheDefs[model];
			var limit_fields = false;
			if (model !== this.model){
				limit_fields = ['id', 'name'];
			}else{
				if (this.options.limit_field){
					limit_fields = this.options.limit_field;
				}
			}
			if (!def) {
				def = modelFieldsCache.cacheDefs[model] = this._rpc({
						model: model,
						method: 'fields_get',
						args: [
							limit_fields,
							["store", "searchable", "type", "string", "relation", "selection", "related"]
						],
						context: this.getSession().user_context,
					})
					.then((function (fields) {
						modelFieldsCache.cache[model] = sortFields(fields, model, self.options.order);
					}).bind(this));
			}
			return def.then((function () {
				return _.filter(modelFieldsCache.cache[model], function (f) {
					return (!filters.searchable || f.searchable) && self.options.filter(f);
				});
			}).bind(this));
        },
    });

    // convert select record function to domain
    const DomainEditorDialog = view_dialogs.SelectCreateDialog.extend({
        init: function() {
            this._super.apply(this, arguments);
            const _this = this;
            this.options = _.defaults(this.options, {
                dynamicFilters: [
                    {
                        description: _.str.sprintf(_t("Selected domain")),
                        domain: Domain.prototype.stringToArray(
                            _this.options.default_domain
                        ),
                    },
                ],
            });
        },

        get_domain: function(selected_ids) {
            let group_domain = [];
            const search_data = this.viewController.renderer.state;
            let domain = search_data.domain;
            if (this.$(".o_list_record_selector input").prop("checked")) {
                if (search_data.groupedBy.length) {
                    group_domain = _.filter(search_data.data, x => {
                        return x.res_ids.length;
                    }).map(x => {
                        return x.domain;
                    });
                    group_domain = _.flatten(group_domain, true);
                    // Compute domain difference
                    _.each(domain, d => {
                        group_domain = _.without(
                            group_domain,
                            _.filter(group_domain, x => {
                                return _.isEqual(x, d);
                            })[0]
                        );
                    });
                    // Strip operators to leave just the group domains
                    group_domain = _.without(group_domain, "&");
                    // Add OR operators if there is more than one group
                    group_domain = _.times(
                        group_domain.length - 1,
                        _.constant("|")
                    ).concat(group_domain);
                }
            } else {
                const ids = selected_ids.map(x => {
                    return x.id;
                });
                domain = domain.concat([["id", "in", ids]]);
            }
            return domain.concat(group_domain);
        },

        on_view_list_loaded: () => {
            this.$(".o_list_record_selector input").prop("checked", true);
            this.$footer
                .find(".o_selectcreatepopup_search_select")
                .prop("disabled", false);
        },
    });

	// add button select record to enable filter in list view
    basic_fields.FieldDomain.include({
        _onShowSelectionButtonClick: function(event) {
            event.preventDefault();
            const _this = this;
            if (this.mode === "readonly") {
                return this._super.apply(this, arguments);
            }
            if (!this.value) {
                this.value = [];
            }
            const dialog = new DomainEditorDialog(this, {
                title: _t("Select records..."),
                res_model: this._domainModel,
                default_domain: this.value,
                readonly: false,
                disable_multiple_selection: false,
                no_create: true,
                on_selected: function(selected_ids) {
                    _this.domainSelector
                        .setDomain(this.get_domain(selected_ids))
                        .then(_this._replaceContent.bind(_this));
                    _this.trigger_up("domain_changed", {
                        child: _this,
                        alreadyRedrawn: true,
                    });
                },
            }).open();
            this.trigger("dialog_opened", dialog);
            return dialog;
        },
    });

    // fix bug odoo when download deleted file
    basic_fields.FieldBinaryFile.include({
    	on_save_as: function (ev) {
			var self = this;
			if (!this.value) {
				this.do_warn(_t("Save As..."), _t("The field is empty, there's nothing to save !"));
				ev.stopPropagation();
			} else if (this.res_id) {
				framework.blockUI();
				var filename_fieldname = this.attrs.filename;
				this.getSession().get_file({
					complete: framework.unblockUI,
					data: {
						'model': this.model,
						'id': this.res_id,
						'field': this.name,
						'filename_field': filename_fieldname,
						'filename': this.recordData[filename_fieldname] || "",
						'download': true,
						'data': utils.is_bin_size(this.value) ? null : this.value,
					},
					error: (error) => {console.log(error); self.trigger_up('reload');},
					url: '/web/content',
				});
				ev.stopPropagation();
			}
		},
    });

    // format number when input data form
    basic_fields.InputField.include({
        init: function () {
            this._super.apply(this, arguments);
            this.thousands_sep = core._t.database.parameters.thousands_sep || ',';
            this.decimal_point = core._t.database.parameters.decimal_point || '.';
            this.re = new RegExp("[^" + this.decimal_point + "-\\d]", "g");
        },

        // remove autocomplete
        _prepareInput: function ($input) {
            var res = this._super.apply(this, arguments);
            if (!this.nodeOptions.isPassword) {
                res.attr('autocomplete', 'nope');
            }
            return res;
        },
    });

    basic_fields.NumericField.include({
        _onInput: function () {
            this._super();
            var self = this;
            if (this.formatType === "float_time") {
                return;
            }
            $(this.$input).val(function (index, value) {
                if (self.formatType === "year") {
                    return value.replace(self.re, "");
                }
                var origin_value = value.replace(self.re, "").replace(/\B(?=((\d{3})+(?!\d)))/g, self.thousands_sep);
                var new_value = origin_value.split(self.decimal_point);
                var re = new RegExp("\\" + self.thousands_sep, "g");
                if (new_value.length > 1) {
                    new_value = new_value[0] + self.decimal_point + new_value[1].replace(re, '');
                }
                return new_value;
            });
        }
    });

    var FieldYear = basic_fields.FieldInteger.extend({
        description: _lt("Year"),
        formatType: 'year',

        init: function () {
            this._super.apply(this, arguments);
            this.formatType = 'year';
        },
    });

    field_utils.format.year = function(value, field, options) {
        options = options || {};
        if (!value && value !== 0) {
            return "";
        }
        return (_.str.sprintf('%d', value));
    };

    field_utils.parse.year = function(value) {
        var parser = field_utils.parse.integer;
        if (value > 9999) {
            throw new Error(_.str.sprintf(core._t("'%s' is not valid year"), value));
        }
        return parser(value);
    };

    // fix bug
    basic_fields.FieldDateRange.include({
        isValid: function () {
            if (this.value === false) {
                return true;
            }
            return (this._super.apply(this, arguments));
        },
    });

    // valid empty space from field
    basic_fields.FieldText.include({
        isValid: function () {
            const value = this.mode === "readonly" ? this.value : this.$input.val();
            if (value && value !== "" && !value.replace(/\s/g, '').length) {
                return false;
            }
            return this._super();
        },
    });

    // add action disable context to field many2one
    relationalFields.FieldMany2One.include({
        start: function () {
            this._super.apply(this, arguments);
            var self = this;
            var prom = this._rpc({
                model: "ir.actions.act_window",
                method: "search_read",
                args: [[['res_model', '=', this.field.relation]]],
            })
            Promise.resolve(prom).then(function (result) {
                self.many2one_context = result;
            });
        },

        _searchCreatePopup: function (view, ids, context, dynamicFilters) {
            var self = this;
            var options = self._getSearchCreatePopupOptions(view, ids, context, dynamicFilters);
            if (self.many2one_context.length > 0) {
                var context = self.many2one_context[0].context.replace(/'/g, '"').replace(/False/g, 'false').replace(/True/g, 'true');
                _.each(JSON.parse(context), function (value, key) {
                    if (["disable_menu", "disable_search"].includes(key)) {
                        options.context[key] = value;
                    }
                });
            }
            return new dialogs.SelectCreateDialog(self, _.extend({}, self.nodeOptions, options)).open();
        },
    });

    // view pdf by open new tab, file type base on odoo: pdf, png
    relationalFields.FieldMany2ManyBinaryMultiFiles.include({
        events: _.extend({}, relationalFields.FieldMany2ManyBinaryMultiFiles.prototype.events, {
            'click .o_attachment_wrap a': '_onFilePDF',
        }),

        _onFilePDF: function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var wrap = $(ev.currentTarget).parents('.o_attachment_wrap');
            var extension = wrap.find('.o_image').data('mimetype');
            var fieldId = wrap.find('.o_image_box').attr('data-id');
            if (['application/pdf', 'image/jpeg', 'image/jpe', 'image/jpg', 'image/png'].includes(extension)) {
                window.open(`/web/content/${fieldId}`, '_blank');
            } else {
                window.open(`/web/content/${fieldId}?download=true`);
            }
        }
    });

    registry.add('year', FieldYear);
});
