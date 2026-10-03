from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Dataset


class DatasetUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="upload-user", password="test-password")
        self.client.force_login(self.user)
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)

    def test_valid_file_upload_saves_dataset_and_redirects(self):
        with override_settings(MEDIA_ROOT=self.media_dir.name):
            response = self.client.post(
                reverse("home"),
                {
                    "name": "Employee report",
                    "file": SimpleUploadedFile(
                        "employees.csv",
                        b"id,name\n1,Ada\n",
                        content_type="text/csv",
                    ),
                },
                follow=True,
            )

            self.assertEqual(response.redirect_chain, [(reverse("home"), 302)])
            self.assertContains(response, "File uploaded successfully.")
            dataset = Dataset.objects.get(user=self.user)
            self.assertEqual(dataset.name, "Employee report")
            self.assertTrue(dataset.file.storage.exists(dataset.file.name))

    def test_unsupported_file_shows_validation_error(self):
        with override_settings(MEDIA_ROOT=self.media_dir.name):
            response = self.client.post(
                reverse("home"),
                {
                    "name": "Unsupported report",
                    "file": SimpleUploadedFile("notes.txt", b"not a dataset"),
                },
            )

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "File extension allowed")
            self.assertFalse(Dataset.objects.filter(user=self.user).exists())


class DatasetWarningTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="warning-user", password="test-password")
        self.client.force_login(self.user)
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)

    def test_date_columns_are_not_high_cardinality_and_empty_columns_not_constant(self):
        rows = ["join_date,notes"]
        rows.extend(f"2026-01-{day:02d}," for day in range(1, 12))
        csv_content = "\n".join(rows).encode()

        with override_settings(MEDIA_ROOT=self.media_dir.name):
            dataset = Dataset.objects.create(
                user=self.user,
                name="Date and missing values",
                file=SimpleUploadedFile("dates.csv", csv_content, content_type="text/csv"),
            )

            response = self.client.get(reverse("analyze", args=[dataset.pk]))

        self.assertEqual(response.status_code, 200)
        warnings = response.context["warnings"]
        self.assertFalse(any("join_date" in warning and "high cardinality" in warning for warning in warnings))
        self.assertTrue(any("notes" in warning and "100% missing" in warning for warning in warnings))
        self.assertFalse(any("notes" in warning and "constant" in warning for warning in warnings))


class CorruptedJsonMessageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="json-user", password="test-password")
        self.client.force_login(self.user)
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)

    def test_corrupted_json_shows_english_error_message_on_workspace(self):
        with override_settings(MEDIA_ROOT=self.media_dir.name):
            dataset = Dataset.objects.create(
                user=self.user,
                name="Broken JSON",
                file=SimpleUploadedFile(
                    "broken.json",
                    b'[{"id": 1, "name": "Aarav"}, {"id": 2, "name": "Priya"',
                    content_type="application/json",
                ),
            )

            response = self.client.get(reverse("analyze", args=[dataset.pk]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The file is corrupted or has an invalid format.")
        self.assertNotContains(response, "File corrupt hai ya format galat hai.")
