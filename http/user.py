class User:
    def __init__(self, name, surname):
        self.first_name = name
        self.last_name = surname

    def __str__(self):
        return f'{self.first_name} {self.last_name}'