
class Pagination:

    start = 0
    end = 0

    def __init__(self, length, limit, current_page=1):
        self.length = length
        self.limit = limit
        self.pages = int((length - 1) / limit) + 1
        self.current_page = current_page

        self.calculate_start_end(current_page)

    def calculate_start_end(self, current_page):

        self.current_page = current_page

        if current_page > self.pages:
            self.current_page = self.pages

        if current_page < 1:
            current_page = 1

        self.start = (current_page - 1) * self.limit
        self.end = self.start + self.limit

        if self.length < self.end:
            self.end = self.length

    def export(self):
        return {
            "start": self.start,
            "end": self.end,
            "pages": self.pages,
            "page": self.current_page,
            "total": self.length,
            "showing": self.end - self.start
        }

