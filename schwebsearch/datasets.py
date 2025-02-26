import os
import shutil
import time
import warnings
from datetime import datetime
from os import environ, makedirs
from os.path import expanduser, join
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import URLError
from urllib.request import urlretrieve

import pandas as pd

REMOTE_SCH_DATASET = {
    "url": "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/certificacao_de_produtos",
    "filename": "produtos_certificados.zip",
}


def _get_data_home(data_home=None) -> str:
    """Return the path of the data directory.

    By default the data directory is set to a folder named 'SCHWebSearch/datasets' in the
    user home folder.

    Alternatively, it can be set by the 'SCH_DATA' environment
    variable or programmatically by giving an explicit folder path.
    The '~' symbol is expanded to the user home folder.

    If the folder does not already exist, it is automatically created.

    Parameters
    ----------
    data_home : str or path-like, default=None
        The path to data directory. If `None`, the default path
        is `%LOCALAPPDATA%/Local/SCHWebSearch/datasets` or `~/SCHWebSearch/datasets`.

    Returns
    -------
    data_home: path-like
        The path to data directory.

    """
    default_data_home = join(os.environ.get("LOCALAPPDATA", "~"), "SCHWebSearch")
    default_data_home = join(default_data_home, "datasets")
    if data_home is None:
        data_home = environ.get("SCH_DATA", default_data_home)
    data_home = expanduser(data_home)
    makedirs(data_home, exist_ok=True)

    return Path(data_home)


def _download_sch_database(
    data_home,
    remote=REMOTE_SCH_DATASET,
    download_if_missing=True,
    download_grace_period=180,
    force_download=False,
    n_retries=3,
    delay=1,
):
    """Helper function to download SCH remote dataset.

    Fetch SCH dataset pointed by remote's url, save into path using remote's
    filename.

    Parameters
    ----------
    target_dir : path-like.
        Directory to save the file to. The path to data directory.

    remote : dict, default=REMOTE_SCH_DATASET
        Dictionary containing remote dataset url and filename.
        REMOTE_SCH_DATASET = {
            'url': 'https://www.anatel.gov.br/dadosabertos/paineis_de_dados/certificacao_de_produtos',
            'filename': 'produtos_certificados.zip'
        }

    download_if_missing : bool, default=True
        If False, raise an OSError if the data is not locally available
        instead of trying to download the data from the source site.

    download_grace_period : int, default=180
        Specify the number of days that must pass before re-download
        the file from the internet.

    force_download : bool, default=False
        If True, re-download the file from the internet.

    n_retries : int, default=3
        Number of retries when HTTP errors are encountered.

    delay : int, default=1
        Number of seconds between retries.

    Returns
    -------
    file_path: Path
        Full path of the created file.
    """
    sch_data_home = data_home / "sch"
    makedirs(sch_data_home, exist_ok=True)
    sch_file_path = sch_data_home / remote["filename"]

    if sch_file_path.exists() and not force_download:
        sch_file_ctime = datetime.fromtimestamp(sch_file_path.stat().st_ctime)
        sch_file_age = datetime.today() - sch_file_ctime
        if sch_file_age.days < download_grace_period:
            return sch_file_path

    if download_if_missing:
        temp_file = NamedTemporaryFile(
            prefix=remote["filename"] + ".part_", dir=sch_data_home, delete=False
        )
        temp_file.close()

        try:
            temp_file_path = Path(temp_file.name)
            while True:
                try:
                    url = remote["url"] + "/" + remote["filename"]
                    urlretrieve(url, temp_file_path)
                    break
                except (URLError, TimeoutError):
                    if n_retries == 0:
                        # If no more retries are left, re-raise the caught exception.
                        raise
                    warnings.warn(f"Retry downloading from url: {remote['url']}")
                    n_retries -= 1
                    time.sleep(delay)

        except (Exception, KeyboardInterrupt):
            os.unlink(temp_file.name)
            raise

        # The following renaming is atomic whenever temp_file_path and
        # file_path are on the same filesystem. This should be the case most of
        # the time, but we still use shutil.move instead of os.rename in case
        # they are not.
        shutil.move(temp_file_path, sch_file_path)

        return sch_file_path
    else:
        OSError("SCH dataset not found")


def fetch_sch_database(
    *,
    data_home=None,
    download_if_missing=True,
    download_grace_period=180,
    force_download=False,
    n_retries=3,
    delay=1.0,
):
    """Load data from SCH dataset

    Download it if necessary.

    Parameters
    ----------
    data_home : str or path-like, default = None
        Specify a download and cache folder for the datasets. If None,
        all the data is stored in '~/sch_database' subfolder.

    download_if_missing : bool, default=True
        If False, raise an OSError if the data is not locally available
        instead of trying to download the data from the source site.

    download_grace_period : int, default=180
        Specify the number of days that must pass before re-download
        the file from the internet.

    force_download : bool, default=False
        If True, re-download the file from the internet.

    n_retries : int, default=3
        Number of retries when HTTP errors are encountered.

    delay : float, default=1.0
        Number of seconds between retries.

    Returns
    -------
    frame : DataFrame of shape (n, 21)

        columns
    ==  ===========================================
    0   Data da Homologação
    1   Número de Homologação
    2   Nome do Solicitante
    3   CNPJ do Solicitante
    4   Certificado de Conformidade Técnica
    5   Data do Certificado de Conformidade Técnica
    6   Data de Validade do Certificado
    7   Código de Situação do Certificado
    8   Situação do Certificado
    9   Código de Situação do Requerimento
    10  Situação do Requerimento
    11  Nome do Fabricante
    12  Modelo
    13  Nome Comercial
    14  Categoria do Produto
    15  Tipo do Produto
    16  IC_ANTENA
    17  IC_ATIVO
    18  País do Fabricante
    19  CodUIT
    20  CodISO
    ==  ===========================================

    """
    if data_home is None:
        data_home = _get_data_home(data_home=data_home)
    else:
        data_home = Path(data_home)

    sch_file_path = _download_sch_database(
        data_home,
        download_if_missing=download_if_missing,
        download_grace_period=download_grace_period,
        force_download=force_download,
        n_retries=n_retries,
        delay=delay,
    )

    frame = pd.read_csv(sch_file_path, sep=";")
    return frame
