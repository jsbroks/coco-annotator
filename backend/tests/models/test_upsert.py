from database import CategoryModel, upsert

category1 = {
    "name": "Upsert Category",
    "color": "white"
}


class TestCategoryUpsert:

    def test_create_category(self):

        query = { "name": category1.get("name") }
        create_category1 = upsert(CategoryModel, query=query, update=category1)

        assert create_category1.name == category1.get("name")
        assert create_category1.color == category1.get("color")

        found = CategoryModel.objects(**query).first()
        assert found.name == category1.get("name")
        assert found.color == category1.get("color")

    def test_update_category(self):
        query = {"name": category1.get("name")}
        set = {"name": "Upsert New", "color": "black"}

        found = upsert(CategoryModel, query=query, update=set)

        assert found.name == set.get("name")
        assert found.color == set.get("color")

