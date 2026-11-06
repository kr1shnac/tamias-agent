"""TODOINC's one product: a to-do list."""


def add(items, title):
    items.append({"title": title, "done": False, "due": "today"})
    return items


def complete(items, title):
    for item in items:
        if item["title"] == title:
            item["done"] = True
    return items
