// Toggles the registration form between private and employer-paid participation.
// If "employed" is checked, the address fields are the company (billing) address,
// the company e-mail is shown and VFLL/membership discounts are hidden and reset.
function toggleCompanyRegistration() {
    var employedCheckBox = document.getElementById("id_employed");
    if (!employedCheckBox) {
        return;
    }
    var employed = employedCheckBox.checked;

    ["employed_note", "company_address_heading", "company_email_block"].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) {
            el.style.display = employed ? "block" : "none";
        }
    });

    var membershipBlock = document.getElementById("membership_block");
    if (membershipBlock) {
        membershipBlock.style.display = employed ? "none" : "block";
    }

    // hint for non-members below the costs doesn't apply to employer-paid participation
    var nonmemberNote = document.getElementById("nonmember_note");
    if (nonmemberNote) {
        nonmemberNote.style.display = employed ? "none" : "inline";
    }
    Array.from(document.getElementsByClassName("nonmember_star")).forEach(function (el) {
        el.style.display = employed ? "none" : "inline";
    });

    if (employed) {
        var vfll = document.getElementById("id_vfll");
        if (vfll) {
            vfll.checked = false;
        }
        Array.from(document.getElementsByName("memberships")).forEach(function (el) {
            el.checked = false;
        });
    }

    var company = document.getElementById("id_company");
    if (company) {
        company.required = employed;
    }
    var companyEmail = document.getElementById("id_company_email");
    if (companyEmail) {
        companyEmail.required = employed;
    }

    // prices are only rendered in the shop checkout
    if (typeof changePrice === "function" && document.getElementById("totalprice")) {
        changePrice();
    }
}

document.addEventListener("DOMContentLoaded", toggleCompanyRegistration);
