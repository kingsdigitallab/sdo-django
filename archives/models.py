from django.db import models


# Create your models here.
class Repository(models.Model):
    name = models.CharField(
        max_length=400, help_text="Enter the current name of the repository")
    identifier = models.CharField(
        max_length=10, blank=True, help_text="Add an identifier for this repository, e.g. NYPL")
    rism_identifier = models.CharField(
        max_length=10, blank=True, help_text="Add the RISM identifier for this repository, e.g. US-NYp")
    description = models.TextField(
        blank=True, help_text="As required, enter additional descriptive text about this repository")

    class Meta:
        verbose_name_plural = "Repositories"

    def __str__(self):
        phrase = self.name

        if self.identifier:
            phrase += " (" + self.identifier + ")"

        return phrase


ADDRESS_TYPES = (
    ('1', 'Street Address'),
    ('2', 'Postal Address'),
    ('3', 'Web Address'),
)


class Address(models.Model):
    address = models.ForeignKey(Repository, on_delete=models.CASCADE)
    address_type = models.CharField(
        max_length=1, choices=ADDRESS_TYPES, help_text="Indicate the kind of address")
    address1 = models.CharField(
        "Address Line 1", max_length=300, help_text="First line of the address")
    address2 = models.CharField("Address Line 2", max_length=300, blank=True,
                                help_text="Additional address information as required")
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField("Province/State", max_length=100, blank=True,
                                help_text="Province, State, or other regional indicator")
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(
        "Postal/Zip Code", max_length=12, blank=True, help_text="Postal, ZIP or other mailing code")
    note = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Addresses"


STATEMENT_TYPES = (
    ('1', 'Format'),
    ('2', 'Provenance'),
    ('3', 'Rights Holder'),
    ('4', 'License'),
)


class Collection(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)
    name = models.CharField(
        "Name", max_length=200, help_text="The name by which this collection is currently known")
    name_supplied = models.BooleanField("Collection name supplied?", blank=False,
                                        help_text="Indicate if the collection name is supplied by the Schenker Documents Online project")
    identifier = models.CharField(
        max_length=15, blank=True, help_text="The code used to refer to this collection in shelfmarks and other identifying information")
    description = models.TextField(
        blank=True, help_text="As required, other descriptive information about this collection")

    def __str__(self):
        phrase = self.name + ", " + self.repository.name
        return phrase

    class Meta:
        unique_together = ("repository", "name")


class CollectionStatements(models.Model):
    collection_id = models.ForeignKey(Collection, on_delete=models.CASCADE)
    statement_type = models.CharField(max_length=1, choices=STATEMENT_TYPES,
                                      help_text="Indicate the kind of statement being made about this collection")
    description = models.CharField(
        max_length=400, blank=False, help_text="Make a statement about the collection")

    def __str__(self):
        phrase = self.get_statement_type_display() + ": " + self.description
        return phrase

    class Meta:
        verbose_name_plural = "Collection Statements"


DELIMITER_TYPES = (
    ('1', 'Slash ( / )'),
    ('2', 'Dash ( - )'),
    ('3', 'Dot ( . )'),
    ('4', 'Space ( )'),
    ('5', 'Comma ( ,)'),

)


CONTENT_TYPES = (
    ('1', 'Correspondence'),
    ('2', 'Diary'),
    ('3', 'Lessonbook'),
    ('4', 'Other'),
    ('5', 'Mixed'),
)


class Container(models.Model):

    collection = models.ForeignKey(
        Collection, help_text="Select the collection to which this container belongs; click the green plus sign (+) to add a new repository to the archive", on_delete=models.CASCADE)
    content_type = models.CharField("Content Type", max_length=1, choices=CONTENT_TYPES,
                                    help_text="Indicate the kind of material included in this container.")
    series = models.CharField(
        max_length=15, blank=True, help_text="As required, enter the series identifier for the container")
    box = models.CharField(max_length=15, blank=True,
                           help_text="As required, enter the box identifier for the container")
    folder = models.CharField("Folder", max_length=15, blank=True,
                              help_text="As required, enter the folder identifier for the container")
    description = models.TextField(
        blank=True, help_text="As required, other descriptive information about this container")

    def get_collection_full_name(self):
        phrase = self.collection.name + ", " + self.collection.repository.name
        return phrase

    get_collection_full_name.short_description = "Collection"

    def __str__(self):
        phrase = self.collection.name + " " + self.box + " " + self.folder
        return phrase

    class Meta:
        unique_together = ("collection", "box", "folder")


class ContainerStatements(models.Model):
    container_id = models.ForeignKey(
        Container, related_name='container_statements', on_delete=models.CASCADE)
    statement_type = models.CharField(max_length=1, choices=STATEMENT_TYPES,
                                      help_text="Indicate the kind of statement being made about this container")
    description = models.TextField(
        help_text="Make a statement about this container")

    def __str__(self):
        phrase = self.get_statement_type_display() + ": " + self.description
        return phrase

    class Meta:
        verbose_name_plural = "Container Statements"


class Document(models.Model):
    container = models.ForeignKey(Container, on_delete=models.CASCADE)
    unitid = models.CharField(
        "ID", max_length=10, help_text="Alpha-numeric text string that serves as a unique reference point or control number for the digital item representing the physical material")
    coverage_start = models.DateField("Start Date", blank=True)
    coverage_end = models.DateField("End Date", blank=True, null=True)
    id_supplied = models.BooleanField(
        "Doc ID supplied?", blank=False, help_text="Indicate whether or not this id is supplied by the Schenker Documents Online project; leaving this unchecked indicates that the document ID is drawn from information maintained by the holding institution")
    description = models.CharField(
        max_length=200, blank=True, help_text="As required, enter a brief descriptive note about this document")

    def get_container_full_label(self):
        phrase = self.container.collection.identifier + " " + self.container.box + " " + self.container.folder + \
            " (" + self.container.collection.name + ", " + \
            self.container.collection.repository.name + ")"
        return phrase

    get_container_full_label.short_description = "Container"

    def get_container_content_type(self):
        return self.container.content_type

    get_container_content_type.short_description = "Content Type"

    def __str__(self):
        phrase = self.unitid
        return phrase

    class Meta:
        unique_together = ("container", "unitid")


class DocumentStatements(models.Model):
    document_id = models.ForeignKey(
        Document, related_name='document_statements', on_delete=models.CASCADE)
    statement_type = models.CharField(max_length=1, choices=STATEMENT_TYPES,
                                      help_text="Indicate the kind of statement being made about this container")
    description = models.TextField(
        help_text="Make a statement about this document")

    def __str__(self):
        phrase = self.get_statement_type_display() + ": " + self.description
        return phrase

    class Meta:
        verbose_name_plural = "Document Statements"
