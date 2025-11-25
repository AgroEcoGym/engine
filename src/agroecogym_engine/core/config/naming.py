


class NameAssigner:
    """Utility to assign unique names to fields and farmers and build readable farm identifiers."""



    def assign_fields(self,fields):
        # Name fields uniquely :
        cpt = {}
        for f in fields:
            if f.__class__.__name__ in cpt.keys():
                cpt[f.__class__.__name__] += 1
                f.name = f.__class__.__name__ + "-" + str(cpt[f.__class__.__name__])
            else:
                cpt[f.__class__.__name__] = 0
                f.name = f.__class__.__name__ + "-0"

        return {f.name: f for f in fields}


    def assign_farmers(self,farmers,fields):
        # Name farmers uniquely :
        cpt = {}
        for f in farmers:
            if f.__class__.__name__ in cpt.keys():
                cpt[f.__class__.__name__] += 1
                f.name = f.__class__.__name__ + "-" + str(cpt[f.__class__.__name__])
            else:
                cpt[f.__class__.__name__] = 0
                f.name = f.__class__.__name__ + "-0"

            #Assign farmer to all fields:
            [f.assign_field(fi) for fi in fields]

        return {f.name: f for f in farmers}

    def build_full_name(self,fields,farmers):
        """
        Builds a standardized name for the farm as a string. example: Farm_Fields[Field-0[Weather-0_Soil-0_Plant-0]]_Farmers[BasicFarmer-0]
        """
        str = "Farm_Fields["
        for fi in fields:
            str += fi + "["
            for e in fields[fi].entities:
                str += fields[fi].entities[e].fullname + "_"
            str = str[:-1]
            str += "]"
        str += "]_Farmers["
        for fa in farmers:
            str += fa + "_"
        str = str[:-1]
        str += "]"
        return str


    def build_short_name(self,fields):
        """
        Builds a standardized name for the farm as a string. example: Farm_Fields[Field-0[Weather-0_Soil-0_Plant-0]]_Farmers[BasicFarmer-0]
        """
        short = "farm_"
        for fi in fields:
            short += (
                str(fields[fi].shape["length#nb"])
                + "x"
                + str(fields[fi].shape["width#nb"])
                + "("
            )
            for e in fields[fi].entities:
                short += fields[fi].entities[e].shortname + "_"
            short = short[:-1]
            short += ")"
        return short