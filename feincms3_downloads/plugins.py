import os
import tempfile

from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext_lazy as _

import feincms3_downloads.checks  # noqa: F401
from feincms3_downloads.previews import preview_as_jpeg

from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField
from filer.models import Folder, Image


class DownloadBase(models.Model):
    file = FilerFileField(
        verbose_name=_('file'),
        related_name="+",
        on_delete=models.CASCADE,
    )
    file_size = models.IntegerField(_("file size"), editable=False)
    caption = models.CharField(_("caption"), max_length=100, blank=True)
    show_preview = models.BooleanField(_("show preview"), default=True)
    preview = FilerImageField(
        verbose_name=_('preview'),
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )

    class Meta:
        abstract = True
        verbose_name = _("download")
        verbose_name_plural = _("downloads")

    def __str__(self):
        return self.basename

    def save(self, *args, **kwargs):
        self.file_size = self.file.size
        super().save(*args, **kwargs)
        if (
            self.show_preview
            and not self.preview
            and (
                preview := generate_preview(
                    source=self.file, preview=self.preview)
            )
        ):
            self.preview = preview
            super().save()

    save.alters_data = True

    @property
    def basename(self):
        return os.path.basename(self.file.file.name)

    @property
    def caption_or_basename(self):
        return self.caption or self.basename


def generate_preview(*, source, preview):
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(source.file.name)[1]) as f:
        source.file.open()
        source.file.seek(0)
        f.write(source.file.read())
        f.seek(0)
        if p := preview_as_jpeg(f.name):
            preview_folder = Folder.objects.get_or_create(
                    name='download_previews')[0]
            filename = f'{source.original_filename}.jpg'
            filer_image = Image.objects.create(
                original_filename=filename,
                name=filename,
                file=ContentFile(p, name=filename),
                folder=preview_folder
            )
            source.file.close()
            return filer_image
        source.file.close()
        return None
