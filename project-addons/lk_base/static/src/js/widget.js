odoo.define('lk_base.notification', function (require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var QWeb = core.qweb;
    var pyUtils = require('web.py_utils');
    var basic_fields = require("web.basic_fields");
    var FieldChar = basic_fields.FieldChar;
    var fieldRegistry = require("web.field_registry");
    var _lt = core._lt;

    var NotificationMenu = Widget.extend({
        name: 'notification_menu',
        template: 'NotificationMenu',
        events: {
            'click .o_mail_notification_action': '_onNotificationActionClick',
            'show.bs.dropdown': '_onNotificationMenuShow',
            'hide.bs.dropdown': '_onNotificationMenuHide',
        },
        start: function () {
            this._$notificationsPreview = this.$('.o_mail_systray_dropdown_items');
            this.call('mail_service', 'getMailBus').on('notification_updated', this, this._updateCounter);
            this._updateCounter();
            this._updateNotificationPreview();
            return this._super();
        },
        //--------------------------------------------------
        // Private
        //--------------------------------------------------
        /**
         * Make RPC and get current user's notification details
         * @private
         */
        _getNotificationData: function () {
            var self = this;
            return self._rpc({
                model: 'notification.content',
                method: 'systray_get_notifications',
                args: [],
            }).then(function (data) {
                self._notifications = data;
                self.notificationCounter = _.reduce(data, function (total_count, p_data) {
                    return total_count + p_data.total_count || 0;
                }, 0);
                self.$('.o_notification_counter').text(self.notificationCounter);
                self.$el.toggleClass('o_no_notification', !self.notificationCounter);
            });
        },
        /**
         * Update(render) system tray view on notification updated.
         * @private
         */
        _updateNotificationPreview: function () {
            var self = this;
            self._getNotificationData().then(function () {
                self._$notificationsPreview.html(QWeb.render('NotificationMenu.Previews', {
                    widget: self
                }));
            });
        },
        /**
         * update counter based on notification
         * @private
         * @param {Object} [data] key, value to decide notification created or deleted
         * @param {Boolean} [data.notification_deleted] when notification deleted
         * @param {Boolean} [data.notification_created] when notification created
         */
        _updateCounter: function (data) {
            if (data) {
                if (data.notification_created) {
                    this.notificationCounter++;
                }
                if (data.notification_deleted && this.notificationCounter > 0) {
                    this.notificationCounter--;
                }
                this.$('.o_notification_counter').text(this.notificationCounter);
                this.$el.toggleClass('o_no_notification', !this.notificationCounter);
            }
        },
        //------------------------------------------------------------
        // Handlers
        //------------------------------------------------------------
        /**
         * Redirect to specific action given its xml id or to the notification
         * view of the current model if no xml id is provided
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onNotificationActionClick: function (ev) {
            ev.stopPropagation();
            var self = this;
            var data = _.extend({}, $(ev.currentTarget).data(), $(ev.target).data());
            var context = {};
            if (data.filter) {
                var filters = data.filter.split(",");
                _.each(filters, function (filter) {
                    context[filter] = 1;
                });
            }
            this.$('.dropdown-toggle').dropdown('toggle');
            var targetAction = $(ev.currentTarget);
            var actionXmlid = targetAction.data('action_xmlid');
            this._rpc({
                route: '/web/action/load',
                params: {action_id: actionXmlid}
            }).then(function (action) {
                if (action) {
                    var new_context = pyUtils.eval('context', action.context);
                    _.each(new_context, function (val, key) {
                        if (key.includes('search_default')) {
                            delete new_context[key];
                        }
                    })
                    var new_action = JSON.parse(JSON.stringify(action));
                    new_action['context'] = {...context, ...new_context};
                    self.do_action(new_action, {clear_breadcrumbs: true});
                }
            })
        },
        /**
         * @private
         */
        _onNotificationMenuShow: function () {
            document.body.classList.add('modal-open');
            this._updateNotificationPreview();
        },
        /**
         * @private
         */
        _onNotificationMenuHide: function () {
            document.body.classList.remove('modal-open');
        },
    });

    SystrayMenu.Items.push(NotificationMenu);

    var FieldBadge = FieldChar.extend({
        template: "web.FieldBadge",
        description: _lt("Badge"),
        supportedFieldTypes: ["selection", "many2one", "char"],

        // _setDecorationClasses
        _applyDecorations: function () {
            var self = this;
            this.attrs.decorations.forEach(function (dec) {
                var isToggled = py.PY_isTrue(py.evaluate(dec.expression, self.record.evalContext));
                var className = `badge-${dec.className.split("-")[1]}`;
                self.$el.toggleClass(className, isToggled);
            });
        },
    });

    fieldRegistry.add("badge", FieldBadge);

    return {
        NotificationMenu: NotificationMenu,
        FieldBadge: FieldBadge,
    };
});
