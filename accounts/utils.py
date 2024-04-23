import random
from typing import NoReturn
from string import ascii_lowercase, digits


class OtpSender:
    phone = None
    otp = None

    def __init__(self, phone, otp) -> NoReturn:
        self.phone = phone
        self.otp = otp

    def send_otp_on_phone(self) -> NoReturn:
        print(f"===> You one time password {self.otp} must be send to {self.phone}")  # bung for this func


def generate_code(length=6) -> str:
    result = ''
    for num in range(0, length):
        if random.choice((True, False, False)):
            result += random.choice(digits)
        else:
            result += random.choice(ascii_lowercase)
    return result

