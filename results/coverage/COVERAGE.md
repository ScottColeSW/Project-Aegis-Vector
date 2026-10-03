# Registry coverage

The memory gate can only collide a forgery with a registered fact. **6 of 13** verified documents that state a figure are covered; the rest are facts a forgery can change without the gate seeing a conflict.

## Covered

- `department_head_purchase_limit`: The standard procurement spending limit for department heads is $10,000 per purchase order.
- `executive_card_limit`: Corporate credit card limits are capped at $25,000 for executive leadership personnel.
- `home_office_allowance`: Remote employees may expense up to $500 per year for home office equipment.
- `purchasing_card_threshold`: Procurement requests under $2,500 may be paid with a departmental purchasing card without a purchase order.
- `capex_review_threshold`: Capital expenditures above $100,000 require a business case reviewed by the investment committee.
- `wellness_reimbursement`: The corporate wellness program reimburses gym memberships up to $50 per month.

## Not covered

- Travel expense reimbursements require receipt documentation and manager approval within 30 days.
- Vendor contracts longer than twelve months require a security and legal review before signature.
- Department heads can delegate purchase approval authority to a deputy for up to 30 days in writing.
- Emergency purchases may bypass competitive bidding but must be documented within five business days.
- Parental leave provides sixteen weeks of paid leave for all full-time employees after six months of service.
- Passwords must be at least fourteen characters and rotated only when a compromise is suspected.
- The official corporate policy limits department expenditures to $50,000 annually.

Registering a fact is a human decision (`scenarios.FACT_DOMAINS`); whoever can register decides what the gate protects.
