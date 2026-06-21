from django.utils import timezone

from events.choices import FOOD_PREFERENCE_CHOICES, TOUR_CHOICES_2026, WS2026_CHOICES
from events.utils.utils import boolean_translate


def choices_to_string(choices_list, choices):
    label_list = [label for value, label in choices if value in choices_list]
    return ", ".join(label_list)


def get_form_template(registration_form):
    if registration_form == "s":
        form_template = "events/add_event_member_tw.html"
    elif registration_form == "w":
        form_template = "events/add_event_member_wc.html"
    elif registration_form == "m":
        form_template = "events/add_event_member_mv.html"
    elif registration_form == "f":
        form_template = "events/add_event_member_ft.html"
    elif registration_form == "f24":
        form_template = "events/add_event_member_ft_2024.html"
    elif registration_form == "f26":
        form_template = "events/add_event_member_ft_2026.html"
    return form_template


def get_personal_form_data(form):
    data_dict = {}
    data_dict["firstname"] = form.cleaned_data["firstname"]
    data_dict["lastname"] = form.cleaned_data["lastname"]
    data_dict["email"] = form.cleaned_data["email"]
    return data_dict


def get_additional_mv_form_data(form):
    data_dict = {}
    data_dict["takes_part_in_mv"] = boolean_translate(
        form.cleaned_data.get("takes_part_in_mv")
    )
    data_dict["takes_part_in_ft"] = boolean_translate(
        form.cleaned_data.get("takes_part_in_ft")
    )
    return data_dict


def get_additional_form_data(form, event, form_type):
    data_dict = {}
    if form_type == "s":
        data_dict["address_line"] = form.cleaned_data["address_line"]
        data_dict["street"] = form.cleaned_data["street"]
        data_dict["city"] = form.cleaned_data["city"]
        data_dict["state"] = form.cleaned_data["state"]
        data_dict["postcode"] = form.cleaned_data["postcode"]
        data_dict["phone"] = form.cleaned_data["phone"]
        # make name of this registration from event label and date
        data_dict["name"] = f"{event.label} | {timezone.now()}"
        data_dict["academic"] = form.cleaned_data["academic"]
        data_dict["company"] = form.cleaned_data["company"]
        data_dict["message"] = form.cleaned_data["message"]
        data_dict["vfll"] = form.cleaned_data["vfll"]
        data_dict["memberships"] = form.cleaned_data["memberships"]
        data_dict["attention"] = form.cleaned_data["attention"]
        data_dict["attention_other"] = form.cleaned_data["attention_other"]
        data_dict["education_bonus"] = form.cleaned_data["education_bonus"]
        data_dict["free_text_field"] = form.cleaned_data["free_text_field"]
        data_dict["agree"] = form.cleaned_data["agree"]
        if event.is_full():
            data_dict["attend_status"] = "waiting"
        else:
            data_dict["attend_status"] = "registered"
    elif form_type == "w":
        data_dict["member_type"] = form.cleaned_data.get("member_type")
        data_dict["attend_status"] = "registered"
    elif form_type == "f24":
        data_dict["address_line"] = form.cleaned_data["address_line"]
        data_dict["street"] = form.cleaned_data["street"]
        data_dict["city"] = form.cleaned_data["city"]
        data_dict["postcode"] = form.cleaned_data["postcode"]
        data_dict["phone"] = form.cleaned_data["phone"]
        data_dict["member_type"] = (
            "o"
            if "vv" in form.cleaned_data["memberships_full"]
            else "k"
            if "vk" in form.cleaned_data["memberships_full"]
            else None
        )
        if data_dict["member_type"]:
            data_dict["vfll"] = True
        data_dict["memberships"] = [
            item
            for item in form.cleaned_data["memberships_full"]
            if item not in ["vv", "vk"]
        ]
        # make name of this registration from event label and date
        data_dict["name"] = f"{event.label} | {timezone.now()}"
    elif form_type == "f26":
        data_dict["address_line"] = form.cleaned_data["address_line"]
        data_dict["street"] = form.cleaned_data["street"]
        data_dict["city"] = form.cleaned_data["city"]
        data_dict["postcode"] = form.cleaned_data["postcode"]
        data_dict["phone"] = form.cleaned_data["phone"]
        data_dict["memberships"] = [item for item in form.cleaned_data["memberships"]]
        # make name of this registration from event label and date
        data_dict["name"] = f"{event.label} | {timezone.now()}"

    return data_dict


def get_mv_form_data(form):
    data_dict = {}
    vote_transfer = form.cleaned_data.get("vote_transfer")
    data_dict["vote_transfer"] = vote_transfer
    data_dict["vote_transfer_check"] = form.cleaned_data.get("vote_transfer_check")
    data_dict["agree"] = form.cleaned_data.get("mv_check")
    data_dict["member_type"] = form.cleaned_data.get("member_type")
    data_dict["attend_status"] = "registered"
    return data_dict


def get_f24_form_data(form):
    food_pref_list = []
    food_pref_list.append(form.cleaned_data.get("food_preferences"))
    booking27_list = []
    booking27_list.append(form.cleaned_data.get("booking27"))
    booking28_list = []
    booking28_list.append(form.cleaned_data.get("booking28"))

    data_dict = {}
    data_dict["memberships_full"] = form.cleaned_data.get("memberships_full")
    data_dict["nomember"] = form.cleaned_data.get("nomember")
    data_dict["takes_part_in_mv"] = boolean_translate(
        form.cleaned_data.get("takes_part_in_mv")
    )
    data_dict["takes_part_in_ft"] = boolean_translate(
        form.cleaned_data.get("takes_part_in_ft")
    )
    data_dict["having_lunch"] = boolean_translate(form.cleaned_data.get("having_lunch"))
    data_dict["networking"] = boolean_translate(form.cleaned_data.get("networking"))
    data_dict["yoga"] = boolean_translate(form.cleaned_data.get("yoga"))
    data_dict["ideas"] = boolean_translate(form.cleaned_data.get("ideas"))
    data_dict["celebration"] = boolean_translate(form.cleaned_data.get("celebration"))
    data_dict["food_preferences"] = choices_to_string(
        food_pref_list, FOOD_PREFERENCE_CHOICES
    )
    data_dict["food_remarks"] = form.cleaned_data.get("food_remarks")
    data_dict["booking27"] = choices_to_string(booking27_list, BOOKING_CHOICES_27)
    data_dict["booking28"] = choices_to_string(booking28_list, BOOKING_CHOICES_28)

    data_dict["remarks"] = form.cleaned_data.get("remarks")

    return data_dict


def get_f26_form_data(form):
    food_pref_list = []
    food_pref_list.append(form.cleaned_data.get("food_preferences"))
    tour_list = []
    tour_list.append(form.cleaned_data.get("tour"))
    ws_list = []
    ws_list.append(form.cleaned_data.get("ws2026"))

    data_dict = {}
    data_dict["memberships"] = form.cleaned_data.get("memberships")
    data_dict["nomember"] = form.cleaned_data.get("nomember")
    data_dict["takes_part_in_mv"] = boolean_translate(
        form.cleaned_data.get("takes_part_in_mv")
    )
    data_dict["dinner_one"] = boolean_translate(form.cleaned_data.get("dinner_one"))
    data_dict["dinner_two"] = boolean_translate(form.cleaned_data.get("dinner_two"))
    data_dict["food_preferences"] = choices_to_string(
        food_pref_list, FOOD_PREFERENCE_CHOICES
    )
    data_dict["food_remarks"] = form.cleaned_data.get("food_remarks")
    data_dict["tour"] = choices_to_string(tour_list, TOUR_CHOICES_2026)
    data_dict["ws2026"] = choices_to_string(ws_list, WS2026_CHOICES)
    data_dict["food_remarks"] = form.cleaned_data.get("food_remarks")

    data_dict["remarks"] = form.cleaned_data.get("remarks")

    return data_dict
