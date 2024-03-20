
class UserInput:

    def capture_user_input(self):
        return input('User says: ')

    def wait_keyword(self):
        while True:
            keyword = input('Waiting keyword: ')
            if keyword.lower().startswith('hey, cozmo') or keyword.lower().startswith('hey cozmo'):
                return keyword
            if keyword.lower().startswith('bye'):
                return keyword
