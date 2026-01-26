class UserMemory:
    def __init__(self):
        self.pref = {"budget": None, "brand": None, "category": None}

    def update(self,text):
        t = text.lower()

        for w in t.split():
            if w.isdigit():
                self.pref["budget"]= int(w)
        
        for b in ["apple","samsung","sony","dell","hp"]:
            if b in t:
                self.pref["brand"] = b.title()

        if "phone" in t:
            self.pref["category"] = "Smartphone"
        
        if "laptop" in t:
            self.pref["category"] = "Laptop"

    def summary(self):
        return str(self.pref)


