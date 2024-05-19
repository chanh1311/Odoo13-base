odoo.define('lk_base.views', function (require) {
    'use strict';
    var ListController = require('web.ListController');
    var KanbanController = require('web.KanbanController');
    var CalendarController = require('web.CalendarController');
    var FormRenderer = require('web.FormRenderer');
    var core = require('web.core');
    var ControlPanelRenderer = require('web.ControlPanelRenderer');
    var AbstractController = require('web.AbstractController');
    var AbstractWebClient = require('web.AbstractWebClient');
    var Dialog = require('web.Dialog');
    var ListRenderer = require('web.ListRenderer');
    var Sidebar = require('web.Sidebar');
    var Chatter = require('mail.Chatter');
    var _t = core._t;
    var _lt = core._lt;
    var qweb = core.qweb;
    var pyUtils = require('web.py_utils');
    var ActionManager = require('web.ActionManager');
    var dialogs = require('web.view_dialogs');
    var QWeb = core.qweb;
    var field_utils = require('web.field_utils');
    var MailManager = require('mail.Manager');
    var viewUtils = require('web.viewUtils');
    var dom = require('web.dom');
    const Menu = require('web.Menu');
    var searchBarAutocompleteRegistry = require("web.search_bar_autocomplete_sources_registry");
    var SearchBar = require("web.SearchBar");
    var CalendarView = require('web.CalendarView');
    var viewRegistry = require('web.view_registry');
    var GraphRenderer = require('web.GraphRenderer');

    // used to format values in tooltips and yAxes.
    var FORMAT_OPTIONS = {
        // allow to decide if utils.human_number should be used
        humanReadable: function (value) {
            return Math.abs(value) >= 1000;
        },
        // with the choices below, 1236 is represented by 1.24k
        minDigits: 1,
        decimals: 2,
        // avoid comma separators for thousands in numbers when human_number is used
        formatterCallback: function (str) {
            return str;
        },
    };

    // odoo expire session
    $(document).ready(function () {
        $("body").click(function () {
            $.getJSON("/ajax/session/", function (data) {
                if (data) {
                    if (data.result == 'true') {
                        location.reload();
                    }
                }
            });
        });
    });

    // display active menu
    Menu.include({
        events: _.extend(
            {
                "click a[data-menu]": "main_menu_onclick",
                "click .o_menu_apps li.dropdown .dropdown-menu": "preventCloseDropdown",
            },
            Menu.prototype.events
        ),

        preventCloseDropdown: function(ev) {
            ev.preventDefault();
            ev.stopPropagation();
        },

        change_menu_section: function (primary_menu_id) {
            this._super(primary_menu_id);
            $('.o_main_navbar .o_menu_sections li').removeClass('active');
            $('.o_main_navbar .o_menu_sections li a').removeClass('active');
            var state = $.bbq.getState(true);
            if (state.action) {
                var current_menu = $("a[data-action-id='" + state.action + "']:not(.o_app)");
                if (current_menu.parents("li:first").hasClass('show')) {
                    current_menu.addClass('active');
                } else {
                    current_menu.parents("li:first").addClass('active');
                }
            }
        },

        main_menu_onclick: function (ev) {
            $('.o_main_navbar .o_menu_sections li').removeClass('active');
            $('.o_main_navbar .o_menu_sections li a').removeClass('active');
            var current_menu = $(ev.currentTarget);
            if (current_menu.parents("li:first").hasClass('show')) {
                current_menu.addClass('active');
            } else {
                current_menu.parents("li:first").addClass('active');
            }
        },
    });

    AbstractWebClient.include({
        // remove title webpage
        init: function (parent) {
            this._super(parent);
            this.set('title_part', {"zopenerp": ""});
        },
    });

    // hide action export
    Sidebar.include({
        start: function () {
            this._super.apply(this, arguments);
            var self = this;
            var export_label = _t("Export");
            this.items['other'] = $.grep(self.items['other'], function (i) {
                return i && i.label && i.label !== export_label;
            });
        },

        // visible sidebar in list view
        _onDropdownClicked: function (event) {
            var self = this;
            this.trigger_up('sidebar_data_asked', {
                callback: function (env) {
                    if (env.activeIds.length !== 0) {
                        self._super(event);
                    } else {
                        event.stopPropagation();
                        event.preventDefault();
                        Dialog.alert(self, _t("Please select a record."));
                    }
                }
            });
        },
    });

    AbstractController.include({
        willStart: function () {
            var self = this;
            var def = this._rpc({
                model: 'res.groups',
                method: 'get_custom_button',
                args: [],
            }).then(function (result) {
                self.custom_button = result;
            });
            // get user_group to set security for customize button tree view
            var def1 = this._rpc({
                route: '/web/session/get_session_info',
            }).then(function (data) {
                self.user_groups = data.user_groups;
            });
            return Promise.all([this._super.apply(this, arguments), def, def1]);
        },

        getViewName: function(viewType) {
            var actionView = this.actionViews.filter(function(obj) {return obj.type === viewType});
            if (actionView) {
                return this.modelName + "." + actionView[0].fieldsView.name;
            }
            return '';
        },
    });

    // add button dynamic import
    ListController.include({
        willStart: function () {
            var self = this;
            var def = this._rpc({
                model: 'dynamic.import',
                method: 'get_import_list',
                args: [self.modelName],
            }).then(function (result) {
                self.importTemplates = result;
            });
            return Promise.all([this._super.apply(this, arguments), def]);
        },

        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.importTemplates.import_len > 0) {
                this.$buttons.on('click', '.o_import', this.import_xls.bind(this));
            }
        },

        import_xls: function (ev) {
            var self = this;
            var id = $(ev.currentTarget).data('id');
            if (id) {
                var prom = this._rpc({
                    model: "dynamic.import",
                    method: "execute_import",
                    args: [id],
                })
                Promise.resolve(prom).then(function (result) {
                    self.do_action({
                        name: result['name'],
                        res_model: 'dynamic.import.execute',
                        res_id: result['res_id'],
                        views: [[false, 'form']],
                        type: 'ir.actions.act_window',
                        view_mode: 'form',
                        target: 'new',
                    });
                });
            }
        },

        // visible sidebar in list view
        _toggleSidebar: function () {

        },
    });

    // disable open popup field one2many
    ListRenderer.include({
    	// prevent multiple click
        _onAddRecordToGroup: function (ev) {
            var target = $(ev.target);
            target.css("pointer-events", "none");
            setTimeout(function () {
                target.css("pointer-events", "unset");
            }, 1500);
            this._super.apply(this, arguments);
        },

        // prevent multiple click
        _onAddRecord: function (ev) {
            var target = $(ev.target);
            target.css("pointer-events", "none");
            setTimeout(function () {
                target.css("pointer-events", "unset");
            }, 1500);
            this._super.apply(this, arguments);
        },
        
        _onRowClicked: function (e) {
            if (!this.el.classList.contains('tree_no_open')) {
                this._super.apply(this, arguments);
            }
        },

        _renderHeaderCell: function (node) {
            var $th = this._super.apply(this, arguments);
            const {icon, name, string} = node.attrs;
            var field = this.state.fields[name];
            if (!field) {
                return $th;
            }
            var node_options = pyUtils.py_eval(node.attrs.options || '{}');
            if (node_options.hasOwnProperty('field_center') && node_options['field_center']) {
                $th.addClass('text-center');
            }
            if (node_options.hasOwnProperty('field_left') && node_options['field_left']) {
                $th.addClass('text-left');
            }
            if (node_options.hasOwnProperty('field_right') && node_options['field_right']) {
                $th.addClass('text-right');
            }
            return $th;
        },

        // render different format
        _renderBodyCell: function (record, node, colIndex, options) {
            var res = this._super.apply(this, arguments);
            if (node.tag === 'field') {
                var name = node.attrs.name;
                var field = this.state.fields[name];
                var value = record.data[name];
                var formatter = field_utils.format[field.type];
                var formatOptions = {
                    escape: true,
                    data: record.data,
                    isPassword: 'password' in node.attrs,
                    digits: node.attrs.digits && JSON.parse(node.attrs.digits),
                };
                var formattedValue = formatter(value, field, formatOptions);
                var node_options = pyUtils.py_eval(node.attrs.options || '{}');
                if (node_options.hasOwnProperty('field_center') && node_options['field_center']) {
                    res.addClass('text-center');
                }
                if (node_options.hasOwnProperty('field_left') && node_options['field_left']) {
                    res.addClass('text-left');
                }
                if (node_options.hasOwnProperty('field_right') && node_options['field_right']) {
                    res.addClass('text-right');
                }
                // add icon to cell
                if (node.attrs.hasOwnProperty('icon')) {
                    var cell_value = res.html();
                    res.html('<span class="fa ' + node.attrs.icon + ' fa-lg fa-fw"/> ' + formattedValue);
                }
                if (field.type === 'html') {
                    res.attr('title', '');
                }
            }
            return res;
        },
    });

    FormRenderer.include({
        // hide button update translate
        displayTranslationAlert: function () {
        },
    });

    KanbanController.include({
       renderButtons: function ($node) {
            if (this.hasButtons) {
                this.$buttons = $(qweb.render(this.buttons_template, {
                    btnClass: 'btn-primary',
                    widget: this,
                }));
                if (this.is_action_enabled('create')) {
                    this.$buttons.on('click', 'button.o-kanban-button-new', this._onButtonNew.bind(this));
                    this.$buttons.on('keydown', this._onButtonsKeyDown.bind(this));
                }else{
                    this.$buttons.find('button').not('.kanban_custom_button').remove();
                }
                this._updateButtons();
                return Promise.resolve(this.$buttons.appendTo($node));
            }
            return Promise.resolve();
        },
    });

    // add button
    var NewCalendarController = CalendarController.extend({
        renderButtons: function ($node) {
            var self = this;
            this._super.apply(this, arguments);

            $(QWeb.render('CalendarView.custom_buttons', {
                widget: self,
            })).appendTo(this.$buttons);

            if ($node) {
                this.$buttons.appendTo($node);
            } else {
                this.$('.o_calendar_buttons').replaceWith(this.$buttons);
            }
        },
    });

    var NewCalendarView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Controller: NewCalendarController,
        }),
    });

    viewRegistry.add('calendar_custom_button', NewCalendarView);

    // disable edit calendar view, now odoo has no option to do that
    // CalendarView.include({
    //     init: function (viewInfo, params) {
    //         this._super.apply(this, arguments);
    //         this.loadParams.editable = false;
    //         this.loadParams.creatable = false;
    //     },
    // });

    // format displayed value yAxes
    GraphRenderer.include({
        _formatValue: function (value) {
            var measureField = this.fields[this.state.measure];
            var formatter = field_utils.format[measureField.type];
            var formatedValue = formatter(value, measureField, FORMAT_OPTIONS);
            return formatedValue;
        },
    });

    // add attrs disable menu to hide button Filters or Groupby
    ControlPanelRenderer.include({
        start: function () {
            var disable_menu = this.context.disable_menu;
            var disable_search = this.context.disable_search;
            disable_menu = disable_menu ? disable_menu.split(',') : [];
            this.searchMenuTypes = this.searchMenuTypes.filter(function (menu) {
                return !disable_menu.includes(menu);
            });
            this.withSearchBar = !disable_search;
            return this._super();
        }
    });

    SearchBar.include({
        // Override the base method to detect a "shift" event to search "AND" condition same field not "OR"
        _onAutoCompleteSelected: function(e, ui) {
            var values = ui.item.facet.values;
            if (e.shiftKey && values && values.length && String(values[0].value).trim() !== "") {
                // In case of an "AND" search a new facet is added regarding of
                // the previous facets
                e.preventDefault();
                var filter = ui.item.facet.filter;
                var field = this.fields[filter.attrs.name];
                var Obj = searchBarAutocompleteRegistry.getAny([
                    filter.attrs.widget,
                    field.type,
                ]);
                var obj = new Obj(this, filter, field, this.actionContext);
                var new_filter = Object.assign({}, ui.item.facet.filter, {
                    domain: obj.getDomain(values),
                    autoCompleteValues: values,
                });
                this.trigger_up("new_filters", {
                    filters: [new_filter],
                });
            } else {
                return this._super.apply(this, arguments);
            }
        },
    });

    // display text on button icon
    viewUtils.renderButtonFromNode = function (node, options) {
        if (options) {
            options.textAsTitle = false;
        }
        var btnOptions = {
            attrs: _.omit(node.attrs, 'icon', 'string', 'type', 'attrs', 'modifiers', 'options', 'effect'),
            icon: node.attrs.icon,
        };
        if (options && options.extraClass) {
            var classes = btnOptions.attrs.class ? btnOptions.attrs.class.split(' ') : [];
            btnOptions.attrs.class = _.uniq(classes.concat(options.extraClass.split(' '))).join(' ');
        }
        var str = (node.attrs.string || '').replace(/_/g, '');
        if (str) {
            if (options && options.textAsTitle) {
                btnOptions.attrs.title = str;
            } else {
                btnOptions.text = str;
            }
        }
        return dom.renderButton(btnOptions);
    };

    // open attachment box as default
    Chatter.include({
        init: function (parent, record, mailFields, options) {
            this._super.apply(this, arguments);
            this.openAttachments = true;
        }
    });

    // preview pdf report
    ActionManager.include({
        _downloadReport: function (url) {
            var def = $.Deferred();
            if (!window.open(url)) {
                var message = _t('Please allow browser to download file.');
                this.do_warn(_t('Warning'), message, true);
            }
            return def;
        },
    });

    // register notification channel
    MailManager.include({
        _handlePartnerNotification: function (data) {
            if (data.type === 'notification_updated') {
                this._handlePartnerNotificationUpdateNotification(data);
            } else {
                this._super.apply(this, arguments);
            }
        },

        _handlePartnerNotificationUpdateNotification: function (data) {
            this._mailBus.trigger('notification_updated', data);
        },
    });

    // prevent multiple click on popup
    Dialog.include({
       renderElement: function () {
            this._super.apply(this, arguments);
            var $button = this.$footer.find('button.wizard_open');
            if (typeof $button.attr('name') !== 'undefined' && $button.attr('name') !== false) {
                $button.on('click', function (e) {
                    $button.prop('disabled', true);
                });
            }
        },
    })
});