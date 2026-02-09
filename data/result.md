
http://127.0.0.1:8000/case/create

{
  "status": "ok",
  "case": {
    "bookingId": "demo-booking-001",
    "createdAt": "2026-01-29T07:09:22.808902+00:00",
    "updatedAt": "2026-01-29T07:09:22.808902+00:00",
    "state": "ACTIVE",
    "mode": "TRACKING",
    "selected": {
      "start_index": 0,
      "end_index": 5,
      "areas": [
        "Area A",
        "Area B",
        "Area C",
        "Area D",
        "Area E",
        "Area F"
      ]
    },
    "emergency": {
      "active": false
    },
    "subcenter": {
      "activated": false
    },
    "personnel": {
      "status": "PENDING"
    },
    "user_note": "Testing case lifecycle"
  }
}