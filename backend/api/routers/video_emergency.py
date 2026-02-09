# backend/api/routers/video_emergency.py

from __future__ import annotations

import base64
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from integrations.firebase_admin import init_firebase, db
from integrations.gemini_vertex_video import generate_video_emergency_response


router = APIRouter(prefix="/video", tags=["video-emergency"])

DEMO_FRAME_B64= "/9j//gAQTGF2YzYyLjExLjEwMAD/2wBDAAgGBgcGBwgICAgICAkJCQoKCgkJCQkKCgoKCgoMDAwKCgoKCgoKDAwMDA0ODQ0NDA0ODg8PDxISEREVFRUZGR//xACZAAACAwEBAQEAAAAAAAAAAAACAwEABAUGBwgBAAMBAQEAAAAAAAAAAAAAAAEAAgMEBRAAAgIBAwIFAgUBBwQCAQUBAAECAxExBCESQTITBVFxImFCFDMjgZEG8LHRFSRyUsFioYJD4cJTomM0kxEBAQEBAAECBQMEAwEBAQAAAAERAgMSQRMxIQRhMjNxkXKBUUMjwdGCFP/AABEIA1IB3gMBIgACEQADEQD/2gAMAwEAAhEDEQA/AOPAYLgMOdQ0RIko/X2IIjewMRi0KJsBnYXAa/CSQMOoBDayz0aMiLDiJMKWIQkcB8BEB0RJgQtsKIkQiY8RMSEoJGS0jKiCRIg0xYRJHkNCo6jBJ8BqEwHCoMwA5gIpJlYcuoXHUaJFGQ38ImIz8JJWA3PQKgDKTbKJ7+sW+CITwTMSsByE1jhKhRFpZYZaBkFL1FE6OhIMA2KUGva+OBjXLNNEumS+wl6K39H+DltcnRqU76f4Cr2EnqY9tPH7uWU7P+lx7yDXplK7sj4a3D8vJfKPQrY0/wDSX8lT7D8P8lwPJfsH5EjvrbVL8KD8qtfhX9B+H+S87+Vt9mH+Ws//AGz0PSlokUfhn4j80VjUKrGISYCGAAiiMFQ1wNCTqxsvCKrGy8IqChkBa0GQCnowZAWHEScigxLkomxGRExHRAUhw0FjI6EkWTPNjRFwSgoMfCXJUoDyTkAkJOIBJJJiGISmMQk6DH54M0NR4ihsBMJi1qEmRfI3P0iIjc8CBtTyFJ9jPGWGPypIBFF4ixbCfEcEaoCkIa3mIoKL7FAKMsRHweYicZeB0VhBSKOoTFrhhPUtCSEUhBJ9chjYmsYwglDqvEvkQtR9XiQl7DZQSpRoRn2DzSvhGglfj9xFKUgVKUolSlKJUpSiX5nrGC6xhmoyLBYSBEph4h61Fw1G9xJsQ5aARDloJDEZWDHQKAT0aFEBLkNCTIg/iCiD+ISbEZEVEbEKhBZAZJICEXDRVoQBHQHuRErDE0ZKYHsEgibkIWSAjQYEQxJ0BqYmA1CK5BZZagiaZHUIXHUYEFQ+HYQh0GAjkATJ8kCKUXRhdIMggZF9x8ZZMq0HQCFMZXLkEgpI+ojIOS5EDq2MyIi8DSiNMfU/qRkNNLxgAPW+lS/20VnnBvRzfSq/21M6QqEUpQWK1SlKDCpSlHCpSlHC/M9Y1CqxqMlGA9wiiUw1HC4ajApNrDnoBWFPQCljoHAXHQOAQpgQIQkUWUhEfiETYjUJiNQBSGhciUxEwz2yHSeEZ7OQgBMkFaksIWCCTF9gkKMMTCACFQ4sNC0MQk2DHozw1HrQRWQDDloLCUpjTOOg+BAQ2AmTGQ/CAjfiDisgDq1hCpQbS2S+oiUsouJsBHQfWIiOrAA2RkrBKEZSAciB0RomI4EKminsZx9RSXrfRnnb/wDyOl3OT6E/2JfJ1RIilKRRilKUMFSlKEqUpRL80VjY6iqxsdTFRhSgiTIajRUBnsEDYE2EQJsAKI6BQYEdGTAsPc3ISYvJKYD6TclyBkqYnDUNiKQ2JKxExAkTERS2JsGsTYGAWnyE2DEsi0CTCyKiw8gAxBoWmGIjQ1GccnhEk2Go/JmixyCI2wGwmwGwKUYvCLGRKQhjKpZYMkRB9MhLTnk0Lisyw1GznxgVQtvkPsKDjoCGwOcMfBmZ6j4PgoBtkZIZGQCMjJUwStDDYsfBmaLHwCGDmxtExMw6SUPVehvKkjtnn/7PP9xr/wDrPQlQpKUo2DFKUoipSlEqUpRL801jI6i6xq1MSMEIEomQDyBHQlaki0RIsZEWRNhVAhwACgGAaSCRIB0eSUwVoSDROTGxYmIcR0RSfIyOgl6jFoDRSxMhwEiomkosiFqTMsFiSBElkgNMYmhMRiCTA88CkMQCZW/qNBlh4jSmIj7AdwgGBQshQkJDgFJwGfqDFfiAWiDCbFwDCqKFGWBZImrLVDYCJaoZCQpNyQRkuREUSQYlEmRHQZniOgUBz0DpFB1Eg9F/Z9/7h/8AE9N3PK+gP/cfwepDECKUpWjFKUodFSlKJUpSiX5pr7DFqLrGIxJiA/EELeoVGJ8hAxJCBsWWbLEGYFLkODFBwGAaVkEsJMhoWOpENCI66gwWhBoVEYgCl6hJi3qhnZCKckMoLFJGSZPKB7k9ioCETIhEyCA46BJi1oHESMctBA2OgiYtRqYhDoaEk4F6lIEdQTDUgmIQPQFnHJINvhFQ65ZGmaj/ALmkkYoPcIgpNRLsFAGQUBAZSlEjiUsSsIiiOgZ4joCBxNeoIUNSS7XpDSvq5/GewPDentq6v/ke4KZiKUoRilKUMFSlKEqUpRL80wD7gQCM1DF9wwBJsdCc8gR0L3EtEdAZliRMAoQyApDKxgGEkESCTEyw1BiWOoi0IOLFoKJNEUtUGKnqhiEUgspDECnqT2F9wuxUZpJkLyF2CIloHFi1oHEIjHR0EIfHQSkfDQQOhoQTSGVFkKgExIJiFJ6Bn4SYksAk1vpka4sy9x8BGU0BsnIIQtQFAFhQETClKJwSKyorCbExHQER1HQFJwUNQEFHUBdDaT6Zxf3PdVvqjF/Y8Ft/FH/kj3W1eaK/+KCzOKUoRilKUMFSlKEqUpRL8zV6DELrDM1DBZIDZJMrJ7gw0YUdSidEiZYgzAKh1iuwysYBpEiO5W8hIohR1BjoTX4mItCCQCJRFEUuwSfAuXYIRT3IkUFhAruG9BcfEHPQqM6WNXhFBrwhEa0CgLjoHAAmdx8dDO+GaI6CUjYaGdjqdAE5EsjuSK4AGPiDYEfEEGiMghcQwAGS7hwfAMyIvDETSlKEFZMCJFgImlKUSoQIQQUODFBwYlqiwsi4hElrpme69OedvD4R4KjX+h7n0t/7Ov8Agot5SESFnFKUoYKlKUkqUpQyl+Z4+FFRVoQSoYDCYsBNhoFF8gw0ZY6hLSgZliDMAq2HWKG1jQEUrJEijoTVqwekOpcsAnolEEoFFSWR3JYikhkkTCWZahA9wioioDXhAQaCUrQKGoC1DhqwExj69BHdD46CVY2oQNrAWjuSAhgrgWKXiGCn4ggdEazPFjUySYLfDGAW+FBIovKCEVyHBKyLArLASaUpRKQgSQlAUBbCgJao6EkIoLEtFMuUe49Ef+zX/I8FW8M9R6JvWl5bfHYRepKc786v+oH89/5GXxvwfQ6ZTmfnvuR/qS9x+P8Ag/DdQpzP9SXuX/VIIP8A/RwfhdumRlI413qspcR4Mkt7OX4mH44/DfCo+FEx1IWmCotI2AyWCxI4Ex1IhoTHUS0RBmFEGYBCHWAw6xoGEEFAR5Crf1ABQEY0kgIMVxGeUGxUtUMl2AUkS0JBloECO5QQkVGdVBJgokIJWocNWAtQlqBRuR8JZRm9h9YkQdeoBMXgKmlajREdR6JGAFz1GMCzQJCNiKQ2Ik6IUkmsC4hsgkeGWBqBnqSioUlKUIGhARDEqUEoCgODACiJaoPgkXDQIQNjqjq7O3y0mtUciDOjtQF0fOfuwPMl7gFJ9MV6heZL3Yt2y9ySGkyfRyr1L5svcvnS9wHgEfRyfUd55HnCQ0ifTD6nyIqKVHQySwWEwWJTEOICDiJOgyzIrJkAQMOALJgNAbKisqCRB1gB1kjDkMFoYKwS1QwW9UMARAT0DAnoGAzBIDuSiqzokSha8QwICJiCEhUP2H16CEPr0ARdyYgdw/wgUfDUeZoD0xGLICzwhMGWgCWmHBi4hR1CTkMFhxAUMgJgjCklEFKJsSQYhElSQAkEoKmQUQaqmGKqCEBp4N22tOambduAul1kdZn68F6xLR1g9ZndhEZZMxaOsvUIyyck+pp8M+KyzbVtsow1yOrtn1QJ78jTjxT3fD+xUVlR1OVLBCBEiQcQEHESdBFmTAieoBAxkBT1GxGAIpShKQ6gBlQjDkGAgyasD1QwW9UMAUi7NAwJ6BBnWrDA7klRnULxDBa8QwIJZMSGShUMbXIV2DrAkbfI1eES9R0PCBSYsfWzKtR9bFUOYMtCSHqIlBweBnki5RcHyJNUgoiYDAE0WGAEpBKUSOMhglajBKSUCVBSlkEgdwC0VyDbEwY0NKTbt2c9vBt2a8zgkDb5qInz8HXh6ErubGv/APp/kw16Bslrbtl8yZnWjgveQ9zVt7FPlHY/I+kU67iv/wCEWYLvyas/Y/7mVXIs45WUK6sDoT7MKdMZ+HhkyunCozOltLsx4OZDbWylg9F6b6alXz7D37GvhcixKyo7XnKCECKRRDgBEbEQpkCJahxAlqBcA9UOQnuhyKhVlRWVDSljKhbGw8JAwxDFoLQxCsMtUH3QD1Qf4kBKgT0GsTYGCT3CBKXKzVajOwpajewgpJCJQqH2DrA7B0gSJ6jIPgXImGgFwcdR8BC1GwYjDwH4gxU3ySLqQjVCrzM9c/8A+Jzb7uqQDk0tQYpWfJRHVLI7JkjLyrMPQ1LD5QkwgqKSUFKUJStRgtahoSpSlCCRYbAYkyDHGeA+LEpZo21vQzNMZSwFp3G6l7v+pl/NzX4n/UDdWYMLm2Z1eNk91KXcbtLeqf3MBr2S5IaSOzBjUxFY0zx1yN2z5kvk9NtPAjzOy8S+T0208Bn1Gf3c/wCv+j87SJjoCxkdD0XmgKVlKKYjYCojoACnRBeoSBeoroPxDEL/ABDUNShkooUUAQsdDQW0OrX0iqCiGiEShWF6oLuQ9UVeP+AJGKmMFzESwQgSmaFqHKX0ilqH4hKYv6QotkLjglCJvYOsVFjawET1JgA9QovsATO4yArIasgvEIw+cumJn6nJgTv63/4k121gE3sWrUCd0dEDCzkpI7o/UOofGBfiGUw5YicUgkGipSlCUINAINAKWCGCJVghSAGESeB0GJGQ0CRzGUC5jKAARvdTGjpbmvr5MU6sGfk9lwKOhsjnx1OjtTNv43RgxguCGGTpjdsn9S+T1O08CPK7LxL5PVbTwL4JrP7z9v8Ao/OvsNWgEl0jFoeg84uRQmiEggmIyICQyKCTY9islEPUBK/EPgK/ENgJQFEr1KgFXqPj4UJHR0QqEEAEKl7kLxsnuXuAEi5jBcxEsEIEpmB6hw0A7jVoJQSiSiJlaCQCeED1gpNbB6xcrBfm4ETneyOv/qMzuQPnZ1FMbqvr4RLg4MzRs+j6LMMQ91Lwptv3ZR1snZgX5pj8yUtWSmJdKrcuL9zo02KSyjhJm/ZXfWkwDrozlKPYHzfsxls4tdQvp69HwTYOiVuewfYV0dBqpSmhg6XHUYT9K7E4zoEQMEa0LepJQwWECxKodHQSg4MomMmuWJEELxIQaLJcGG6Zr3MsR/g50nky7qomt8nT2xy69TqbYzdPjdGAwVWOMnRDtvZ0yR7DaeBfB4ypfWvlHs9mv218E1n95+3/AEfnq0mOhEg46HoPOCUpQpEgogoOISMrCBeoBAvEPjoJXiHR0KocoYUdAe4RAr3GrwiV4hq4HoRIIFBCMXuXuUq1YBSKmNYmYiFdwWFEFlMwLU0RjwIWpog+BIQJcBTkkZXbl/UInyn7CZW4Fzu9jO7csSbO1sXn7l6eMkAFerkPnACj9QU5/hEFTIkWBL5Y2giI6DxyJDQBO6xlc2mmjOOgMoOx1eZVqKrtlXLpRnosceG+GHY0XzQdSb4TCo3FcHjJl29nXWk9FwDZV0Sz7goSunOSkuqIMWY6b+l4ehrXPMRaSmi5INFkDBJYLCYLJWhEoglACw1FRCJQQwe78K+Dmt8nUs/cr+6OfZXgz7aeP3WrU6m2OXUuTqbcxdPjdCsejNAeiWsaaV9cflHstmv218Hjtt+pH5R7LZfpR+Caz+8/b/o/O8/EFHQsuZBRXB6TzCu4RX4ilYhUHEqCSBixoFjIgzXI4ewIatAEhqQcTAdwihE4sMPEPEQX1GgnoUIMhIkKkER1JJjqAq0KsHMXNCBKBZLeBbLiUx1JuvUFhamWd6gvuZZ2Ob5ZBNsvcmKduRWSiobk2adttnPlk1QrrWZ8kT3so/TWule4oRvH5P0L4l/4iFNr7oBuUm23/wDkmGorhqlksgcc5RIlKeBsORJoh9MPkFAOA68EAZwyifLBEQUEDCZCzsgut5FpdyRU17e9wkvY6cn59eV2/wADhdWDZt90+jApw7nJ0NpPqjhnOhamzpbJIIyNOCLpxhBE2+JF8vzVygUCq/qJnW9S4VLGq1YM7F81lxgo6c4P8PIsIiRe5UQwk5eFmW01/wD1Mw2amfa/H7iq8R0Kjn06nQqMXT42ys0xM1ZpRLeNW28cfk9lsv018Hjdt44/J7HZfpr4JrH7z9v/ADH57/EEBDxB/jPSeYD8QWCPxjMFRNgEMiANriEwaXAMhuOBUkD0jeliNS4FxQ1aFYEoHqgsBRiTJE4vQQX1DRdXiG4B2KYktFiQTCrAqf1SGdhFf6khUcKnIZN4EvTIgTNdzLdelwhW533VlR8P+JnoXnP7BBM5ZYtsK5fX9PhAZIhywkwYk5QkeW/cgjqJX1CREopIkRSkpCkxdOAkAkMjAFUpVU5DI0tsaoygGAUq8EpD/Ln7BLbyYRJKzdDZ+4Nm0fZALANr4LOpx1A0JU0ReGdfZ2/30ONHlGzb2dBRjqynlmiqfBzK7czN9TEByUbNSqiMe7Jx3GRXUibDGWyvHIBqtj9BlS+oGDBgsNgtAUav0mYp6m1fpMxT1J7V4hVeI6FXY59PiOhV2MXZ42qvU11mSvU2VIEaxr2y/cj8o9ftv04/B5bax+uPyeq2/wCnH4Jrl+8/R/mPzzDxDPxCYeJD+56LzwfjGi/xjDRFCOrFD60JH0gyQ0jpElDUuCOgZjgNKIrksiVqWSIVAVxwxpFYxxB0MCgWMUQSaoCEribHyM0uGwCOcjk73e9WYQ8Pd+/2J3u91hB8d2c3q6mEok8mnauSyZx9ACZ0c8ibVhmrpym/+kwyn1SY6lS8kE4+4NVijK1kGMepmymlDqgKvIxVGqNBpr2ymR6lfD/LnqkYqTqLZJE/lkH1H4bmqkdGtG38qNhtEC9H0MlNOWbI0f8AgbKNilyavISKlH0MUdqnrj+B9W1i+OP/ANRpqp5OlTXVHH0JsvWXbBH0uPH0v+n1B2bCGP05nZSh9yHV1l+n8oeL3+wdbyk8HJspknoe73m1jJNM4G52nQ3hE3lccWEcamitFtpefsHXXhGVi5TEa6nOeImXBs2xUoVscelYG0rCEdQcZ4GhGnC6WjHOGDVCeSzp6llELYivgvQ46kSYSNeBmKfiZtj4WYpeNkdq8RlOpuXYyUrk2IydvjatvyzpUQ7mDbLk61UcJDFNe0j+5H5R6WtYikee2i/cj8noloiq5Puf0z+X50h4kPlqKgvqQ+ep1uIsPALHJcGsSHBpriJSNda4EF6C9AZRSHoJ6cDEiXHIkvpLgZ0AtAsHQwiSworBWgWKnSFoLYzsLl75SXu3hf1M60BY0kcfe7zWMf5ZG/8AUNYQfyzlSm5PLAKZz6mQgS5ARmiL6Ixx3MmTRTy4oS0zs8uqS7s5yOnu68L+Dn4AeUIeoZE18s21QyKk00nQppwRTVjU30xRm0kRCg1VVKPJKWB1ZKpE9PUHGhBRG1irC/IQyNWOw9INJDqcRFNIKMfcLAa4LlAyuvuommEcamVWSQXXP3NWNbEHZalWYPzUofhM9tzs1bS9ivifgPQ1SsjIw7qOdAoTX3InNMn16PpxyLKYN8yBl0QWFz9zdZTXPth+6MtlXR90R10qRn+46vqf2LGt9w/CROjYfmKhryAruTPZYLTeSr0DpxuZor3GeDlK3oQyq7JPqVI23c4ZnlqMhb1Gqraq0M6HGWPhZjn+ozs2bGVfKOVesTYO1eP3Mp1NcTJTqa4mTs8bftdUdivRHH2uqOxToWDbtPHH5PQPscHafqR+Tu9kNc33P6J/L88RGARDOpxoHIWhqNIkSRpr0FQWR8EUA8FwESKEIZgiOqHpBEnADiaMASGktRIaCKyKuM9k1FNvhLlnmvUvUXuW4R/S/wAQ/WPU3dLy6niCfLXc5Lln4I6XE5IIJMxEgWEgWIoNm18cTGjTQ8CWzd3Z4MDGWS6mBqCjyZRDLOnt4cmKiJ1aY9MUZtmiqOTXCIimJoRK5DBkWKDQDY0RY6JniOiHS0xGREwGBiTUEJTGxClIXUCSolyozUPnUBxh7sOYtr6QaOEkE4IaItVYBgYyE1yNhWOhhSqAupNqghd0RgVybY9InJsvWDFMIJ6yVYhA2qGQLdPbLqSOnC11rg5NUXFajPPkiS6T3Vr+DJua3ZyBt9zziXJsljpz9g6PH0c6pYZriZ619X8mr2Mvd3eNt2up16NDkbU6tDNYmuns/wBSPydyzhRONsv1I/J2btIjHL9z7cvzzAZhi6zR2O1xlobEAbEuJNiPrERH1gA0kpKQppkIdxqIgSy0oFTGgWR4BRLSMu+t8qi34ZtXEDk+tWpUk1ceStk3LP8AItPIT+oHQ562giQSQaIiyIK3kdKBsBQ2GgSKTCr5YEhlGpFGN23hlnRhojFtjbDsZto2VDRVQ5AXE4GRISGxgGgZFDooXFDoIBGhiBQxYKgIwOqQtcmiroWoUD8onyx0ZQGpRZaGF1imsHV8uBkvrw8oRYGgRs48l6OCKpmx9RoguC+WNggKBgCcco0Sh7C5R6QRNcrcnPmdPdQ1Zz5opLMaK56YAxkNQ6dCFNif/khsK4WLlmKp8m6C44FYattLPBsasjV9ZO3Gb6xSo44EeWKGpp9jHt5ZNqM/d1+Ns2x06DmbY6VJfKa7Ox8a+TrXviJyfTfGvk6e6/CVHL91M75/jXwCA4TAcdrjD3HwM3cfAuJOQ+AhD4AA0JCwigaq9AmuRUJ4QUp6BQmQDLkrJor+E8x/aC7MvLR6ZvEGeI9Tvdu4m+wKvlh7AkSkCc9bYMNC0wwAkgkgVKhsRSGoJSx1GorVmrbwJoxrpRtqRnqiba4mdbw+ofHUTWOgSqGjISEZDyEtUR0DCrGu46FwlryXJn835L5oloU+R0bDn+YFGwKcdONuDVC44n5hofVug6nHY84CTyc/8yGtyHQ9JzQXQK80bCaY6fSvlkqAYahkk4X0FdZpUOC+WhOOTuNpnQ4t9bhJpnrpVZMG79O81cx/nuAceYaHVPq4ZO4olVNxx8MiqWH4SFYb+Xa5RsoXHIyDr8sS5dDytBLVD6ZY9xW9hnGA4vrh1LsR5sHxMnRjNtv+5tQlbfpeYaMch10+Jp2+p1aDlbfU6lBcHqu36Z40dLe/hOb6Z418nS3v4So5fu/3Of7X5/rHiKxx2uID1HVixkS6k1D4GdD4AAYaAK5DpaYaEsXVLglsKRrTkueyBb4AcsDSz+q7tbbbtZ5fB4+yPVW5PVnT9W3T3F/SvCjk7iePpXYztXyykFKY1rBIYhaDQREUpRKUGDEISbXqbKDHVqb6MLUyrSNlRsr0MdVtcWP/ADNZNXy1wGGH81BF/PRApuyH1HP/AD1RP52HuIt3UFGTM1dqlzkPrQlp6y9Zn6i9QS0dZDv6BHWJtk2DS1PdIv5zoOU7gHcw6XY/1FDY+q1nnpWNi+qXuOoeqXqtfuEvVI+55RSn7jlKfuOl66PqkTbt9/GfdHjqZzTWXk6VTfZ4BpevqvjLualBSR5Sjc2Vvl5O7st8ppRk/wCR0tbjhhdGUFxNB16E0uJ6j6erE5RXJ52cXXNo95bTlZPKerbXyrG1ozMS9nPPDHXV9+xz6LOiR06n5yElbWTUXFibn9RrlS4PJguf1BGN+y3HS8S0Nd3lv6ovXscimXJtixdPja9vqdKg5u31OjQach073pniXyb9+/CYPTPEvk1eov6kVXN5/wB/j+x8GQ5aChkXwdrjEg0LXcZEKaPuh0GZ+6HRCBjZcgMoC0V6EuXIEAXqDRsPzwY95uFTXLnl6GjscH1W9yn0rRBtDHKutzN933ZjnJtj7Wkm+7Mpha0kSUpQatQ0ASOkwkAMJSSiCVqSLRUN8wREdGBNipReYwc2v3HRgh0I/YHqH0sf7pP7ht6V7F6V7D6h9P5ZYZHRYzpXsEor2JX6TaLHBm6M+pGBGiuWBVjUmFkUnkImismKkxrFSAWaVeGR5YyYOQlHlRL0RJ5JiJxVXEbGuJCQyEkFOCUcaGuifHwIUl7GitRAcaoPKNdLfYzVV5OjRThEacbdpfZDjOV9zr0vPJyaa+fg6u10H1HGzpzE8165R3PV1LKON65Rmpsmrrw0X9RsoucGc+XE38s0QeUKbHQs3eTFZLqZCeS2BDB1M3VSOdWzbUxdHjdGlnSoZyqWdKhmnI9fN6D0x/Uvk0eoS+pGT07xDN4/qKrPuf8Afz/Z/wDXxFjI8IF6EI7XmiWrGQYlS5GQCJktEMhIUHAAYNyIUyCMBDGpaAN4ZYaFckA0Uremts81vZ9c38nW3t30dK7nA3c+lk0YyXPkWS3l5IMsWpBJA4cEUggRwSDQCDQgMlakEoCmuuHGWNQqp8DeoFGHwGmWM2xnVL3M2x3APUhf1e5Agb1BKRn6iVIVRqTGweTLGQ6qXIRbaxgurk1KvJNEkTM1Shgy3cEkiTByVsCTLKZTwFCWRDYSlgUtaNVG18w5XntDqvUZ16NgF3P9Ku1J/IXIwbf1vc51O3tPVarcKxYfuJJpcts/3U8HepqygvyNW7p4w8mat27GzyrPA/DL2+zMrBbIPolg6e1OROzn/uOo3Thw2QXoqTJ6tV1Usu13PVgbv+aQjXzC9NWv5YyvwjN9HG5l/wAmVLgIJr5YdkMIWn0sap5CBUPEbKgEl7IOOotfG30HT2+pzKDp7fU0jTp3Nlqgt34gdkTu/EDoP+bf9cz/ANfF/wAIPYjP0l7Hd9XkqtRkXhC1qGtCrSamGmLTDRPqFchJgEodQ0R0Fyl05yFKWF1IwXSnZox0su4t82zMdEcfeWdUzrT/AGk2cK2XVJmdrSIJAJEqyYg9w0BUQSQSSCUGgEGgkZSlEdNrtxwxqms6mUNMFVG6M4xQMr8C6a3a9QrqXEONJ0n8yD+ZEJENcgwNao2qQSYutfSMSJsPPR0JD4SwzPFGiGoFujStDo1L3MW1WcHWoocyatmtr4yjlbrU799E4duDk7ujuSXMAmxrgD0FpKSc+DbHbrysmdLAyNs46MSxS1ZCWRko8keVIoMb9ht+to9FX6FleZ5mO55zZ2yoaOlG7cbp8Pj5M1On6f6rbs7fLfgz3O495Ruo9WEzDttlV+X6pxzIB4q0BYR33YeIhU2Nio1u1m6ja4WSLyXR2WePk7LSlU09cHK2aw0dZL6WCq493z71rbdG74XD5ERq4R2PXqsXpnNiIUi3bSXIuMWdZx66NOTm2/tsQFFMbEzxtiNrsTC0ldDbnU2+pyaDq7bU0io7mzLu/ETswd14gdK/5P8A88/+visPCRkmHhIPQeSlajIIWtRkQdEz2DQHsGhFBJBIMA2X6TObOXTI3y/TZilX3IS5u+v6Y47s5R0fUVyjnAraBKUoDYoYAaEyIJIJJFMdRiFx1GIIJCBCQqiQkTFDVWZ1ciaJ9EjRZPriI6EGip0OFeWEqV7jMBJB9R9AEsDYoNVjYwwTaM5DGA6qGWVRNFUMLJOtJy6Owqyeo9L26bR530/VfJ6r0b9VZK8YeTlt9T9PUo+HHB4/fbbplKLWjPo++inFfCPJerbTP1oryxh4/nXiLq3GYPSde7ar25Ms9uYOiVz5RwBg2TpaA8sR/wAM2AkP8svlid/C1RydLZPy2jHTA3VQaAl2o7nKSQSrdrQvZ7SybWUeg2np8Y4cjTx8I9ZO32SWDdHbqKNcKoxQXSjS8I9bPRVh5OnFfSZox5N1cfpRh5GnP8vLf2joTh1rVHm1wey/tDR+y/g8aZrb9nJWfSznepx6LWvubPT/ANYw+qvrvYrYRtUnFgRRK8WoEOzt3odfbanD2z0O3texpyuO/s9AN34g9noL3fiD00n6nxSPhIIj4Sna8lI2IpDYldEzsVMAkEEzJOReScgIpTyJt8IxirAJrj+oanOOhv8AmZz2TWsCUIEgaoaADQigkgkQFEMCIYSJBIqQ6NYimuOWaUiaqxvSvYyq+SegNQGKsaqxiyVUNVKGqAfSHSUopBYG9BPSkCqheB9SyLwPo8YBjq7Cv/E9N6dxJHntosHe2GpXjT5XqNys0p/Y491SnHDR3qsW7RP7HIvWGbeX645/H9LXmN9tXW9ODnyqTPS7yrriziWw6Hg5a6pXNsoM8qGdOSB6UK3L8pl8pnRlSpacAfln7iBNVeDqbGjzJr7CKds2zt7HadHPuPCfI6vp+2jHB2VSjj1SdRo/OWe51xyt0+mACaehi/MSm+WPqmR30vjltqjlnQrSwYNuzo16HL5Glcb+0Ef2X8Hgnxk+hevr9l/B4Nxy2iV+P3O9MXVac71P/wD0yOlTW6uUn/Qxepx/ebEHORE+OQ46kWLgRjZsLOo9BtXoeX2U/Lf8np9g89JfLaPSbX9Mz7p/UaKf0jHe/qD00n6nxaD+kkCHhCR2vIGhkRSGREDOxKI7ExAVLqRIiAkbMG63Ua+NWbmefvzOc/kVAtt8yTbM8w5VzSyLx7kWDFKUoMFARBIhEEkEgEaDQCDQSfXHLNVccsz1G2girh8YYQXQEhsI5M2/MBGsbGAyMBqrBDharJ8saohYDoYUoYBnHHJowJt4Q6LP3NO28Rl1Zp22v8CY7O1mdba29MkcGqfTI31X/cvlPb1213/RDGcxfb2CyrXlHndvuuzfB0ttusd+C/iM/hmbuPSmjzm8liT+T1l0VdX1I856tseiDt7GFaRy+v7hJ5McZ9mPhMhcrTAdXX1Mz1m2rsWLZRtlFZepshPoEV2dSX2GdSZty5u9p/novnozgh0PS2RtNFdpzYs01t5Rj3005jvbZnWr8KOLtHodmrwox7Pl9nK9e/RfweMpx53J7T13ml/B4dvptYYPHu7iisaI4/qu11kMq3884zlezNe+ir9j1LXBoLyfcrB6uSmbSCr1PQek2ZST1R5+vU7vpPjDy0j2FP6Rz9w/3Gb6X+0YNx+oy+mk/U+MLhEsiOhLOt5CUMiKQxFk3PBKfAHYgkwTkFUJGR8IKpN0uH8HFt8Z0728P4OdNZnAg4s0nAwS1OlZX9D+Dmy1Y2jiClKDSEkpQlQkgQgAJBoBBoRaKuxupMFRup7AtbRsiPgZUaqzJry0QHoREcgQUkkElIQZ5/XLAyyWBdfiGQrKnoiRXwFdPPAjqwODGyNzQ5bg5ytGqwR11Kt20baN809Tgxn7Giu3BNo49psN+pLpkzoONdi4w/s1k8LV6g69Jf8As6mz9a95f+x0LyD1n0d0N3VL6dWvY40J9nqewe9r3NTUuTxm5Xk3yX3AZMa67DZVacyE1jJorsCLr124HxuTORG5odC80jHp0/MXuT1mBWj655I9SmyHJsqRjr7Gysn/AGeXU2jO3S/pRwdo+TtVPhGXSfIyesLNL+Dwl0X5kj3nq3NLPG2JKxhg8OfXW/NOlZ5le0s+Aq6Yz0WGZvV9xOmpVRfyXOFXr8POS8T+SqRJBIw2rU7HpVuLeTk1o3bTh+zDz81x7am6HlamO95nwclR3tVeU+uAp7+9awZpVzyPmkSQIyJ6jqecLIUWLTJTCB+S9QvJIlLkHCXAgNEim58MwVrrtbeiNd3hMm38UyBOt8LOZdHDz7nTs8LOff2Kos5SggSkpSiKhAhCCUSyESxEyuzBvonoctanQ2+iJsacuijRVLgyQeUOreGRWvLbGQ1SMsZDYyIW0ZL1CuojqCVseWLzglsXMUlbjc9Bz7N1dN8Gm5ZBrqCMiNtdN8TRtUhSgl2CwI2NEJi79zPp6YC8MvltkhjL1Xt6s0UzuT1YXlMdCGBW7G137jBZMN1jutbY6qngme3xzoIYXW+w6M+kzeFhqQnGuNuRsZmJMZGeAc1GfN0ITNVczmQma65k9Uzl06bex0aZZRxa5HU20+CdDmOvtHyjtVaI4W0fKO5T4UDo33I9R/Rl8Hhd3fi1/J7v1D9KXwfM/Xr/ACLXj3YweI6tO8Va5aycXd7t32Nt9ziz3dljXLHRk2tTdGNPWMgsozwH1E2DDq32G1zcbF8gRSC6fYEmLleo2l6dXS+6Is21E3lrk5+xuyl9ja7Mlap8lRJCJZ1uFJKFhIJMJBJJKlKUSVdPhoz0/i+TRJZM8Y8y+QCOT4Zz7JOTZp3E+iOO7MYiEpSgSkoJIiIpSiTAGwhYkSOjtnwjmmvby4QK05dOOg2tmauWUOg8MzrXlqixsWZ0xiZCz8lFZCyEjAmicgTYUFuKZcYLkuRGVUEgUEIaLgJCzRCIBSqzVTBC4Lk1UL6iVt9FSiib6oyjoMjwi2eEti4l0OlizTujKS2EpDFIz5DTBBa4SNdUjBBmqqRPRjpVHS25zaexvpehCZHY2mqO7S+EcHZ6o7VT4QKFi+oP9p/B8o/tC/8AdSPqXqD/AGmfI/Wb/O3Ugwf9MKQ6DERfYfA2iKen9I+pmf8ACWqbUxoR04eEbEQuEh8dDNXLRsLf3ZwOkcCuTq3Ucd9TuxkpLJUq3y9EMlEM7XCAOAsKLCTS5ByZL73AktuS5OR+csL/AKhNdhLqiFxORkXqEu6BnuPM5TwQVun1z+AZ+EqBsl2CICkECREgEk/UiZUUqDKRABgMIoHUzcWJDgCmV06ZmuJzaJ9jo1PKM615aYDBEXgbkhYsk9YptlyxEzrI6gclEpKXMYxFOzOgScSZnJ+4UbGhLVDGR8bIxZg62XrYl14Si9Gb9rDPJ56uclozbTvp192Bb0OgMpLBz6vU4zWJDfNUllSFGEbrUxWcGm6eWZrH1CNJyMhIUxleoqaIM01S5M0B9epHSnUokdChnMpeh0KWQh29o9Dr1y+k4m0OpVPgFVzWf1vcdO0n24Z8m3E3ZY5v3PoP9qNzjaTw/wALPnFkshhHDlmiBmreDTFm3LPowmvxABR1BS6UX1wX2HVy4M9PhHIkYGHO6R2PAciH6qZ1ovrivdEKfNmAwmBLQ73CghAWT6YiPMm/CEtpk3NfUsg+Zb7i7J2sks7FS1DbAyAoCQJIk7rIcsiyiRlIRIRCGAGJSWJSxJhGAECEVJRBUJaqNTpVaHNp1OhVoZ1py0JjExCY1EtBFKCJXIE7AbBLbY4RuZVYLL0stJylkOLAhAaqmBaSMhKixhrZzZK/QBTaGRsTGR9OskPXpUoaiLKpexPntfiZq/IqAn8usmYEvcz93/UZXd1cMP8ALRFyqw+OBRpo2vUQh9Wpa2mBpqiIgaajLoWuk6FBgqN9HYCXY2vBsdnBiqa4B3d/k1tgM+jyv9qN47J+UnpqeYNvqm4d1spZ1bMGTbmJ0ZojojMaI6IrE6PIyIgKMhsF1tt4R3cxba3sa48mdCCz0cmmrccGKx9i1k1fNeMyBLQPpAlodzjZZyzLAXUWcO61AggEzxFdeQsYQa0EsF9OOUZGdWyPUjn3V4eUJDTDrGzp6SNvwOt0AWN8FGRh1jPy4khBl6HkJRCJYQIRBEUpQwpKUoRUgpAkyE+lnSosykco1bazHBFHl1ExkWIhLKGxZDaGkPgvUVvIiW11AdA7BSiQojoA4CQQ5aoYD+kypsLqfuS1jbCxDVYsnPjZgYrALkduvfRgsJLP9/sV7jzfscquafyaYS6fkUWNjocu6Ant4x7gLcSBlY5askMR5cTPbVjlaDyJcrBAWMTXIyEsEzhgDQqUZWyuRprkYK5GquRHSo3VzOns3k5FfJ1dpwZfUHUjLBxvXt/5dbgnyzo22quDkeI9W3bvtlzwitBzZTbfJKFMOJ0YzsMRorllYEQDjwwk4q1DlH6ERFCT9s/3EdRLCyYNnV1PLOje8VpIi/MwmzXJEGTPSIJKo8lqJmelo9Cz2/v/AFE7v0GUctI7XI829AcD7KJVSaktAMCS+sJMiUUwYpoSa8MzWUdRoQbWQFlhQoi7kbYrUx36iVoh9LNEUL23hHALDPUDIdgoIpaICBBYUlKUSIpSj9fcUYIyTkjAlAyuXSxZJNgx1qLMo0pnL21vY3wmTjSU9SJyLCJUYUAMRQSTgnAjA5LkLpL0gUjIWSMBJFGUcJtGiFrkIjDI+EFEgT4vJIMRiiQUokuhRGlyFdDNOCMIMoYXCOB0AAoA0t1B0qHg5VBshb0kAn1TeeXU0vY8bbPMmep3iV9UjylixJh8ZAHEANGzKmRfI9aozR1RqXYItcv00BRF2y+y7j1HNaQcK/Ij/wAhI4/TYlA1zy0Yqf1Ub58pDTCZeEsIdSLPQZRoYtHqPylRnu2i7co3CZnc4nif7QemZTnBcnk9OPY+les0Ke3k/fKPm9n6k/kSUyorKiVJCBCCCx7nP3Wp0I9zn7rUQatr+kg2Bs/02GwFkv1M5pvM4RUAMASIkghAJhIJQipSlIKClKJTGTi8o3UX9XBgJjJxeUJldmE8jUc6i/PDNcbGTY2lakEhMJ5GZJUYEkAnkbERi4LgIkVAwGoExiMQpTCI+MAIDoEWKSoDEkUjJAq4ghdQIRUpRc5ABLJhqJ6wlMS2Vz6WM805zuwJnuWIa7UbIvucTe7XpubUuJcl2+5l5nLN24rU61IPP0RriSqa+4SrZt8tYF4SNU2kwreTVGGgCnEbCQhrbCUYR6pfwhMpuyQq2fAMJ4wxHW6KShljKrur6TA72+DRs+bDOjD720i7a36S7zQRttGS0e6k8IzzsLbaYb7+k6tcuEepyzW/hnzm79Wfyz1++9QzmKfY8dZzdIGrwDKiZEItmrKVlCRR7mbc19x6eAbOUIEbSzpk4vuaWYsdEsmqFikhKLK1JGGa6Xg6Ri3MOciSClKTggKUoAGiQUSUClIZAKowoJQCpJBIpFCXSzZXemYQovAKvmurCwfGzJzKbTXGeQL1tjIbGRkhPsPUgKlaEwjOpBqeBaeo3IaZn8wvmEn1NSngbGwweYwlYJ9TpRuC60zmeaxiuZNitbnIHzDN5wErck4GtTsEym2Z/MfuR5j9xA/IPmCOtl59xI5TyC+QBsMCSeYvKNkN5OcVAROHdCuY8ovGbodFnQ2Lr6LH0vhhbPdqPFvIjdW1qx+RxyFNFdT5MsLkmv6hMZSsfLHV8MINM6+qr7oyxcvCzoVtKOWLXl+ZnAiTCLOhs1yBmOkUP28SaqI3egOyq8zqH3VdaNO2rjXBJL5IsbSuhbeuxwfVt+1+3DXuzRut15a6U+Tgbrc9c22bM2Pd3vy5Sb5lwcqLNO9sysIyRfCDx7su+hsqKVl6i3VbJAbJWgQEisgoSVfXxlCITcWb8KSwzLdTjlCTIW51Fbh8ik3EGTbfJBAwA2D2DoIKUoASFkEgApKUpVFSlKABFKUSoSBCQqMr1NVbMsdTVWSs+Eh8bOxnXYYIxoUyeszpkqTEdP6yOsVkpKjusvmCiRJvmE+YJJE6b5hPUxQaEiySQg0ibRlVIJIlILBI6Hy8kOhv8fSOiOqh1MTrPVt9zY8eYxk/Tb9errOlVUoo2VRyOoeWnXZU/qQOp6q/0+u5cpZOHu/SL4NuHKK1FrDGfQzVCXVytTDZCVbxLhoKq1xCqOkpskRXPqG5CWzbxcmdOqCjE5W2s6WboXhqdamvp4XV9iIXqvx1zXxyDCwapJ68lWBz5uo8zvt7rFP5ZyrLZS5LJuTyxdv6Zk2Zr59TFxegDbbJRruOS03JIARXqUgpSjpSmFkBMFyCWiLAtawZncJla29QlpcYMVKr25A6yq0AAlFoUOlPIsBCUpQFJSlEqUpRFJSlEqUpRKoOJCQaQBHHU1VmaOppqAtoihiwDBB9IinpBcWgw1HIkglDvKRfLJUWSM6CehCS8E4GdJPSJAojEiVENRJUhRDwEkF0gowKRIeCCRVI1bczmjb6iW+OhppEQQ+JWsq1ICyKcQVJoyeobvyq+DZj083vV+5IzJDrZeZJsBErjRVwgnNgrhEJ5YcOt9PLNcDNtEbMFce6BxlgLrFlLxDy9yxY0Y91Zj6UdTf1dN9hxbnmTMXSSwoghF3PZgMkAjIBFkjzBbmLbDgClNxFuxshy9wGyg1LkCmQ2DkkjciMkEBw4IgpRoYpSlGKSUpQlBJSgwUlKUkpDBCQSlBxBSGJE0iQ+oRFGitAVGuoaKqGoK1DRKRJJEVRKgxFHQXpDKIg6SVEPBOBIUgkg0iUiRDhkh4KRTEEBlwAUYNu2rMyR0dtHERSfCI1LBa0G4m7G0DeFk8/6lufMn0rRHV9Qv8Ay1b+6PNWTc22+5Ug9ULZEWCEiaF6O6w4ai0hkAymV09obDJtDWa8e7MDByExQS43rNv71nR7HCnqzbu7nO1v3MU9WYNigxb1I6zTWNo5MXOZDlkXJ5BB1LmA5MFglHUtspBQghvkpSgsKSlKIqUpRFSspAlKZIJJJSykEA0BBxQIcRUPBKRKQSiApSDSISDSBViih8EKijRBCMNgh8ELih0UIiwXBIeBECCL0hYAVCIIERBIEJAIkSiESgikpSSLBUJEBxiHCOmHVI6lUMIw0R+o61VXCBIz7TBYQTXA1VpGX1Tcra7f2N3PXnfWN07rWk/24HMbDsm7JP7vLFslp6lGwiLrWWa4VhoUKQSWA+ggKGra24eDfk5FcumR06pdUUacnTBTGimJeMlLL+4EgesXZYYNkTkKbIlIA0jGpcgcglKMSQC2TkBUpShIO4YIQlJSlIFIJZFDaCSgsjUZVCKUpIJKUIRQaK4CEaoaIRSkEkT0hqJLRCQxIqQcUKhQgaIQBhEckEJBRQaIRABNQ1CYMfASnBcBlwJB0k9AQRJCok4JwTgRRgnBOAsCIUgkiUgkgUhwMgiqIyKwQdPoXKOlTPsc6nVGw08bHtq6zzXrl/5qzoi+I+x0t9ufIqk88vhHnZScm5PuaxlWTmLx/wCyrMmHby0Mpq7sODDaacamlxSIjoEaBoRctQwJAShao6W28JzEbKLOxHAtjYJQkii+eyYtyBz9wSMFOQSkMqhqMlAJCVeCClIpSUpQaKCSCStIilKToqwAwStKlLgoCoYAYlSSAkAVNVOhmNdBIw9IPBMUaFWsC1jNgdXAZ5aCSwAYJLBJBJUDBZCADERwNEDPA0QARhAhAKlKUSvUUCRMQEwJERDihFKQSRKQWDOilIZ0v2Coj1SOxTtE1ojRDi5cSXuJLk6t/p0XosHA9S/276A8xPXbLudxPcSblp2RjsnjgKy0RnqZvOWXQq/rka0Jrh0oag88phpeSEyclArAYbFyJKBtE/qEExl0sAutF5QQimfUhgS+clBKAUgSL3IYgggpSDEkkEir3UpASx0jhCWOpV3CRZSUpSLCAlEE/cUjIKURVIkpRFIQIQqU2bcxmvaeNEF06q+7NHQRXHI7ArhXQXoG9JekRhfSRgbgjAIsvAaRcBJCCUOghcY8j4AERSlCUglKSVDigEMRJGhkQEHEq0iDQAyCywTkW3Y1dUs+x3aI8HK2lbhFe7OirOiJ0eOMPIu6vjtouTa4Xc8Jvtw9xdJ9jq+s+oO76EzgTZrOWNoJE1rkX3HQWETFU8lELQlBiTEyciwgERSlZRKkLzyMkL7mfSmvbWY4Ny5OXXLDN1dmUEvneSQQxSBlCkCKoghIpQWFQ4gBJ4JEZBGSBKCSlKlSpSl4Iv1FSlJRZQSmEQDCpP3IJHCIpSjgxJp2njRmH7fiaJL0NWg4Tt9B5Na8oKUoqDgnAZQCBIJInBKQilDIg4CARFKUSguAyAFCQ2IOA4rAP4hFglE8EpAFR1HiFGrbr6kVyl1KeOk5nqnqqjmut/LGb/1BbOH/AJNfSzy87HPLbOiMKi65tmXzMsts8vCBhDJSMNgssaB4UEgwmZDixSGIKRdw8gZLkYRoJgIMAgYqQ+QmRHQog+TZVPgxaM0VsReGKUEJE3kEkETElBJERFKUhK5wTnJGMlwIpKCSGFJSlHmFSYkBAwpyCUkopJRBISMjBSSBiUNq8aFkxfK+SjHpNtoPMm1f0r+DWZVrypUUqAoRSlFYiChISlBIElAIylKJSUpRIgkCEICCTFhIAnRWWaFNURcmZ63jk5XqO/lZLy1xFF8MfIXu93Pczc5v4XsjFKxsCc2wDWMRasdWhVSyzRwiigJMAoSeEmKiGEiKCUCRp8jUxKYaYBMAkggQUSZ6hRlgieoAreRIJB/xFKlBKIqSQSKVyUpQKSmUgkQUkhMlsEKSlKGFQiEGJCX/ABJKEpQWASkERSlEVJKXAC7np1nXFLujonB9OucJr5PQRamsomt+VwXAWC4AKChYKKogYAEIpCBJARFKUjSkIEINpSUpQygkJCwo8ah0h31yopfPLPPyn1c5yP8AUdy9xZ0p8IxaG3DDvozJfEBqMj9JcZDUenAeQFIllJGVAoJEiZEYJQ7sEoZBILERphRYslMAH5IbFFAKsXJ5GCJaiqPKAhA9RP1BSgZJYZSueQwEioJgyoqKgCkpSiClKVCUhIELhiUkkaFZOlSlL/gCUiKUoSpJGSRFISBRIk6mXRNHpdq8wR5Y7vpd3mQ6W+URWnLpFKUltKkgkopEUpRVKkkgkiiIpSiUhAhCVKUuoYV0MG93v/1r+WM3l/kZh3fc5Mn1PLNPH42PfaWJnImyeEBD6zosxhpla7jCIrBRDVJyQUBo0w0xSDiJMD6gShwj6gWyCjihJhZQskmwNH1Ei9AlITgupi5ruELkIvJt8CwmCkJUpSBASJBCiJGUpSKKlKUMKlKEEoC4SIC6chIc5DIUSSZCFkorKgU+4kVlRWMNilKUsxIUJe4BQCcbPTb/AC7F7dzBGXYZVLolkjqHmvWKUZrKJOZstx1YTZ0sk2ugRSCSSIpSkLiSSCQERSlCUhEIMkhK5KEXJ8JEnM9Q3Dm/LXCRcRax7nceda/bsJk8IuOnl8gN5OqXJI5LdtqMdY2EOlAwQ78IZA1SMFIDgagkEkcOiDgAFEKjighxJKCksEIpyQUoKUElJAYkGRSiLxxJBIlBc41RPhIz1sQVBxAXHAcRIiAiAWFSdCNSeEIKT7ABR5CIg1wDoGIoz/BfuX5KNKCopUNIgQiCcKkEglCMoJPh7E+5EhkeRSYaYaqNVE5QZ29rf1xSZ5+MjftLtDLppy7iCEVzyhhKjclAJBYqDJBJRAiKUoClDEKykZbt9jwBkLVu7FRW37nEss6nkO26d8m5Pj2M7fSdU4+jl8nkDN5ZCIk1/JYlMvVhkXjgPICWSY8FafmMggIMoYEpIMhv0VgkEgUEgYODJTwDEMHyKc8AlyDkQGQXqKJ9KMl6yGQI4IpS5EXkvYj/AD/zJ9i/5/5gPKJdiwLLsWAD0n/qJgR/1BQCjr2SUpRV7qgvcEL3Ggv+T/wJjqR/k/8AAmOojDI/3/qie5Ef7/1RPcRvziJaoCQctUBIHfyT79f2i/CQv8ifwkLv/BPfsIwPxL4DA/EvgRvyE9P6kfh/n/siXp/Uj8P8/wDZFjULUZLRfyLWoyWi/kgwPZfIaB7L5CQaI0adp4zOaNp4x6PH6o7tHhQ8RR4UPM+m4goghRJikssSssSKIivUpXqQSN3+lL4OUzqbv9KXwctnTwx8q9hctRnYXLU6J8nLfmQ/GMQuXjGIi/P+ppi7BMFdgmXBiFqGAtQwQKggkgPXyaQa8P8Af7kRJXh/v9yxGB0mJZa/0LEstf6E9AMFhAsM+cEJJBISv9//AGivUv8Af/2ivUAxSGSQwHr5v//Z"
# -----------------------------
# Models
# -----------------------------
class Frame(BaseModel):
    data_b64: Optional[str] = Field(None, description="Base64-encoded image (no data: prefix)")
    url: Optional[str] = Field(None, description="Public/signed URL to an image frame")
    ts_ms: Optional[int] = Field(None, ge=0, description="Timestamp of the frame in ms (optional)")


class VideoEmergencyReq(BaseModel):
    videoUrl: Optional[str] = Field(None, description="Video URL (YouTube/short links supported via backend download)")
    frames: Optional[List[Frame]] = Field(None, description="3–8 sampled frames for analysis")
    fpsRate: int = Field(1, ge=1, le=60, description="Frames per second used to sample frames (context)")
    note: Optional[str] = Field(None, description="Optional note from user/operator")
    store: bool = Field(True, description="If true, store latest result into Firebase")


class VideoEmergencyResp(BaseModel):
    bookingId: str
    at: str
    isEmergency: bool
    confidence: float
    signals: List[str]
    summary: str
    recommendedAction: str
class VideoEmergencyDemoResp(BaseModel):
    at: str
    isEmergency: bool
    confidence: float
    signals: List[str]
    summary: str
    recommendedAction: str

# ✅ NEW: debug response model (no bookingId)
class VideoEmergencyDebugResp(BaseModel):
    at: str
    isEmergency: bool
    confidence: float
    signals: List[str]
    summary: str
    recommendedAction: str

@router.post("/emergency-demo", response_model=VideoEmergencyDemoResp)
def video_emergency_demo(req: VideoEmergencyReq):
    """
    Demo endpoint:
    - does NOT touch /emergency/{bookingId}
    - always uses DEMO_FRAME_B64 if frames not provided
    - no Firebase, no case lookup
    """
    now = _now_iso()

    # ✅ Always have at least 1 frame
    frames_payload: List[Dict[str, Any]] = []
    if (not req.frames) or len(req.frames) == 0:
        if not DEMO_FRAME_B64 or DEMO_FRAME_B64.strip() == "":
            raise HTTPException(status_code=500, detail="DEMO_FRAME_B64 is empty")
        frames_payload = [{"data_b64": DEMO_FRAME_B64, "ts_ms": 0}]
    else:
        for f in req.frames:
            if not f.data_b64:
                raise HTTPException(status_code=400, detail="frames[].url not supported; send data_b64")
            frames_payload.append({"data_b64": f.data_b64, "ts_ms": f.ts_ms})

    # ✅ ensure Vertex SA path is correct (doesn't touch firebase auth)
    _ensure_vertex_sa_env()

    # bookingId is irrelevant in demo
    context = _build_pure_video_context("DEMO", req, frames_payload)

    try:
        out = generate_video_emergency_response(context) or {}
    except Exception as e:
        return VideoEmergencyDemoResp(
            at=now,
            isEmergency=False,
            confidence=0.2,
            signals=["video_analysis_failed"],
            summary=f"Video analysis failed: {repr(e)[:240]}",
            recommendedAction="NONE",
        )

    is_emergency = _normalize_bool(out.get("isEmergency"))
    confidence = _normalize_confidence(out.get("confidence"))
    signals = _clean_signals(out.get("signals"))
    summary = _clean_summary(out.get("summary"))
    recommended_action = "TRIGGER_EMERGENCY" if is_emergency else "NONE"

    return VideoEmergencyDemoResp(
        at=now,
        isEmergency=is_emergency,
        confidence=confidence,
        signals=signals,
        summary=summary,
        recommendedAction=recommended_action,
    )
# -----------------------------
# Helpers
# -----------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _case_root(booking_id: str) -> str:
    return f"/cases/{booking_id}"


def _store_path(booking_id: str) -> str:
    return f"/cases/{booking_id}/video_emergency/latest"


def _normalize_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        return s in ("true", "yes", "y", "1", "emergency", "urgent")
    return False


def _normalize_confidence(v: Any) -> float:
    try:
        f = float(v)
    except Exception:
        f = 0.0
    return max(0.0, min(1.0, f))


def _clean_signals(v: Any) -> List[str]:
    if not isinstance(v, list):
        return []
    out: List[str] = []
    for x in v:
        s = str(x).strip() if x is not None else ""
        if s:
            out.append(s[:40])
    return out[:10]


def _clean_summary(v: Any) -> str:
    if not isinstance(v, str):
        v = str(v)
    return v.strip()[:500]


def _is_youtube_url(url: str) -> bool:
    u = (url or "").lower()
    return ("youtube.com" in u) or ("youtu.be" in u)


# ✅ Fix 1: ensure VERTEX_SA_PATH is absolute and valid (no touching GOOGLE_APPLICATION_CREDENTIALS)
def _ensure_vertex_sa_env() -> None:
    """
    Fix Vertex SA file path without touching GOOGLE_APPLICATION_CREDENTIALS.
    Uses VERTEX_SA_PATH if already correct, else sets an absolute path safely.
    """
    # if user already set it and file exists -> keep
    existing = os.getenv("VERTEX_SA_PATH")
    if existing and os.path.exists(existing):
        return

    # build absolute path: backend/secrets/vertex-service-account.json
    # current file = backend/api/routers/video_emergency.py
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    candidate = os.path.join(base_dir, "secrets", "vertex-service-account.json")

    if os.path.exists(candidate):
        os.environ["VERTEX_SA_PATH"] = candidate
        return

    # last fallback: allow user to set a relative "secrets/..."
    rel = os.path.join("secrets", "vertex-service-account.json")
    if os.path.exists(rel):
        os.environ["VERTEX_SA_PATH"] = os.path.abspath(rel)
        return

    raise RuntimeError(
        "Vertex service account JSON not found. "
        "Put it at backend/secrets/vertex-service-account.json OR set VERTEX_SA_PATH to its full path."
    )


def _download_video_to_file(video_url: str, out_path: str) -> None:
    try:
        import yt_dlp  # type: ignore
    except Exception:
        raise RuntimeError("yt-dlp not installed. Run: pip install yt-dlp")

    ydl_opts = {
        "outtmpl": out_path,
        "quiet": True,
        "no_warnings": True,
        "format": "mp4/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    if not os.path.exists(out_path) or os.path.getsize(out_path) < 1024:
        raise RuntimeError("Video download failed or produced empty file.")


def _ffprobe_duration_seconds(path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {p.stderr.strip()[:200]}")
    try:
        return float(p.stdout.strip())
    except Exception:
        return 0.0


def _extract_frames_base64(video_path: str, count: int = 3) -> List[Dict[str, Any]]:
    if count < 3:
        count = 3
    if count > 12:
        count = 12

    duration = _ffprobe_duration_seconds(video_path)
    if duration <= 0.1:
        duration = 2.0

    ts_list = []
    for i in range(count):
        frac = (i + 1) / (count + 1)
        ts_list.append(max(0.0, min(duration - 0.05, duration * frac)))

    frames: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, t in enumerate(ts_list):
            out_img = os.path.join(tmpdir, f"f{idx:02d}.jpg")
            cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(t),
                "-i",
                video_path,
                "-frames:v",
                "1",
                "-q:v",
                "5",  # ✅ lowered JPEG quality
                out_img,
            ]
            p = subprocess.run(cmd, capture_output=True, text=True)
            if p.returncode != 0 or not os.path.exists(out_img):
                raise RuntimeError(f"ffmpeg failed extracting frame: {p.stderr.strip()[:200]}")

            with open(out_img, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")

            frames.append({"data_b64": b64, "ts_ms": int(t * 1000)})

    return frames


def _build_pure_video_context(booking_id: str, req: VideoEmergencyReq, frames_payload: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "task": "VIDEO_EMERGENCY_CLASSIFIER",
        "bookingId": booking_id,
        "fpsRate": req.fpsRate,
        "note": req.note,
        "video": {
            "videoUrl": req.videoUrl,
            "frames": frames_payload,
            "frameCount": len(frames_payload),
        },
        "instructions": {
            "scope": "video_only",
            "must_not_use": ["lookahead", "tracking", "route", "chat", "history"],
            "output_schema": {
                "isEmergency": "boolean",
                "confidence": "0..1 float",
                "signals": "list[str]",
                "summary": "short string",
            },
        },
    }


# -----------------------------
# Main Endpoint (with Firebase + bookingId)
# -----------------------------



@router.post("/emergency/{bookingId}", response_model=VideoEmergencyResp)
def video_emergency_decision(bookingId: str, req: VideoEmergencyReq):
    if not bookingId or len(bookingId) < 6:
        raise HTTPException(status_code=400, detail="Invalid bookingId")

    if (not req.videoUrl) and (not req.frames or len(req.frames) == 0):
        raise HTTPException(status_code=400, detail="Provide either videoUrl or frames[]")

    init_firebase()
    now = _now_iso()

    case = db.reference(_case_root(bookingId)).get()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found for this bookingId")

    frames_payload: List[Dict[str, Any]] = []

    if req.frames:
        for f in req.frames:
            if not f.data_b64:
                raise HTTPException(status_code=400, detail="frames[].url not supported; send data_b64")
            frames_payload.append({"data_b64": f.data_b64, "ts_ms": f.ts_ms})

    if (not frames_payload) and req.videoUrl:
        try:
            if _is_youtube_url(req.videoUrl):
                with tempfile.TemporaryDirectory() as tmpdir:
                    video_path = os.path.join(tmpdir, "clip.mp4")
                    _download_video_to_file(req.videoUrl, video_path)
                    frames_payload = _extract_frames_base64(video_path, count=3)  # ✅ reduced frames
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Only YouTube URLs supported for auto extraction. Otherwise send frames[].",
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)[:180])

    context = _build_pure_video_context(bookingId, req, frames_payload)

    # ✅ Fix 1: ensure Vertex SA path is correct (doesn't touch firebase auth)
    _ensure_vertex_sa_env()

    out = generate_video_emergency_response(context) or {}


    is_emergency = _normalize_bool(out.get("isEmergency"))
    confidence = _normalize_confidence(out.get("confidence"))
    signals = _clean_signals(out.get("signals"))
    summary = _clean_summary(out.get("summary"))

    recommended_action = "TRIGGER_EMERGENCY" if is_emergency else "NONE"

    if req.store:
        db.reference(_store_path(bookingId)).set(
            {
                "at": now,
                "bookingId": bookingId,
                "isEmergency": is_emergency,
                "confidence": confidence,
                "signals": signals,
                "summary": summary,
                "recommendedAction": recommended_action,
            }
        )

    return VideoEmergencyResp(
        bookingId=bookingId,
        at=now,
        isEmergency=is_emergency,
        confidence=confidence,
        signals=signals,
        summary=summary,
        recommendedAction=recommended_action,
    )


# -----------------------------
# ✅ Fix 2: Debug endpoint (NO Firebase, NO bookingId)
# -----------------------------
@router.post("/emergency-debug", response_model=VideoEmergencyDebugResp)
def video_emergency_debug(req: VideoEmergencyReq):
    """
    Debug endpoint:
    - NO bookingId required
    - NO Firebase
    - NO case lookup
    - Just extracts frames + calls Gemini video classifier
    """
   # ✅ Allow empty request if DEMO_FRAME_B64 is set (demo mode)
    if (not req.videoUrl) and (not req.frames or len(req.frames) == 0):
        if not DEMO_FRAME_B64 or DEMO_FRAME_B64.strip() == "":
            raise HTTPException(status_code=400, detail="Provide either videoUrl or frames[]")


# ✅ if user didn't send frames, use demo frame
    if (not req.frames) or len(req.frames) == 0:
        frames_payload = [{"data_b64": DEMO_FRAME_B64, "ts_ms": 0}]
    else:
        for f in req.frames:
            if not f.data_b64:
                raise HTTPException(
                    status_code=400,
                    detail="frames[].url not supported; send data_b64"
                )
            frames_payload.append({"data_b64": f.data_b64, "ts_ms": f.ts_ms})


    # auto-extract from YouTube
    if (not frames_payload) and req.videoUrl:
        try:
            if _is_youtube_url(req.videoUrl):
                with tempfile.TemporaryDirectory() as tmpdir:
                    video_path = os.path.join(tmpdir, "clip.mp4")
                    _download_video_to_file(req.videoUrl, video_path)
                    frames_payload = _extract_frames_base64(video_path, count=6 if req.fpsRate >= 15 else 3)

            else:
                raise HTTPException(
                    status_code=400,
                    detail="Only YouTube URLs supported for auto extraction. Otherwise send frames[].",
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)[:180])

    # ✅ ensure Vertex SA path is correct (doesn't touch firebase auth)
    _ensure_vertex_sa_env()

    # bookingId is not needed here; send a dummy
    context = _build_pure_video_context("DEBUG", req, frames_payload)

    try:
        out = generate_video_emergency_response(context) or {}

    except Exception as e:
        # show real error in response (demo-safe)
        return VideoEmergencyDebugResp(
            at=now,
            isEmergency=False,
            confidence=0.2,
            signals=["video_analysis_failed"],
            summary=f"Video analysis failed: {repr(e)[:240]}",
            recommendedAction="NONE",
        )

    is_emergency = _normalize_bool(out.get("isEmergency"))
    confidence = _normalize_confidence(out.get("confidence"))
    signals = _clean_signals(out.get("signals"))
    summary = _clean_summary(out.get("summary"))
    recommended_action = "TRIGGER_EMERGENCY" if is_emergency else "NONE"

    return VideoEmergencyDebugResp(
        at=now,
        isEmergency=is_emergency,
        confidence=confidence,
        signals=signals,
        summary=summary,
        recommendedAction=recommended_action,
    )
