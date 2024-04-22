from typing import NoReturn


class OtpSender:
    phone = None
    otp = None

    def __init__(self, phone, otp) -> NoReturn:
        self.phone = phone
        self.otp = otp

    def send_otp_on_phone(self) -> NoReturn:
        print(f"You one time password {self.otp} must be send to {self.phone}")  # bung for this func
