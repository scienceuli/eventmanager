from events.utils.email_utils import send_registration_emails


class NotificationService:
    def send_notification_emails(self, event, form, member, strategy):
        formatting_dict = strategy.build_formatting_dict(form, event, member)
        vfll_sent, member_sent = send_registration_emails(
            event,
            form,
            formatting_dict,
            member.attend_status,
        )

        if vfll_sent:
            member.mail_to_admin = True
        if member_sent:
            member.mail_to_member = True

        member.save()

        return vfll_sent, member_sent
