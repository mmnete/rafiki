import phonenumbers
import random
from typing import Optional, List, Dict

class LocalizationManager:
    """
    Manages localized messages for a multi-country user base.

    This class determines the user's likely language based on their phone number's
    country code and provides translated "please wait" or "I'm busy" style
    messages. It is designed to be easily extensible with new languages.
    """

    def __init__(self):
        # Maps country calling codes to a primary language code (e.g., '49' for Germany -> 'de').
        # This is a sample list and should be expanded based on your user base.
        self.COUNTRY_CODE_TO_LANG: Dict[int, str] = {
        1: 'en',    # USA, Canada
        7: 'ru',    # Russia, Kazakhstan
        20: 'ar',   # Egypt
        27: 'en',   # South Africa
        30: 'el',   # Greece
        31: 'nl',   # Netherlands
        32: 'nl',   # Belgium (Dutch)
        33: 'fr',    # France
        34: 'es',    # Spain
        36: 'hu',   # Hungary
        39: 'it',    # Italy
        40: 'ro',   # Romania
        41: 'de',   # Switzerland (German)
        43: 'de',   # Austria
        44: 'en',    # United Kingdom
        45: 'da',   # Denmark
        46: 'sv',   # Sweden
        47: 'no',   # Norway
        48: 'pl',   # Poland
        49: 'de',    # Germany
        51: 'es',   # Peru
        52: 'es',    # Mexico
        53: 'es',   # Cuba
        54: 'es',    # Argentina
        55: 'pt',    # Brazil
        56: 'es',   # Chile
        57: 'es',   # Colombia
        58: 'es',   # Venezuela
        60: 'ms',   # Malaysia
        61: 'en',    # Australia
        62: 'id',   # Indonesia
        63: 'tl',   # Philippines
        64: 'en',   # New Zealand
        65: 'en',   # Singapore
        66: 'th',   # Thailand
        81: 'ja',    # Japan
        82: 'ko',   # South Korea
        84: 'vi',   # Vietnam
        86: 'zh',    # China (Mandarin)
        90: 'tr',   # Turkey
        91: 'hi',    # India (Hindi)
        92: 'ur',   # Pakistan
        93: 'fa',   # Afghanistan
        94: 'si',   # Sri Lanka
        95: 'my',   # Myanmar
        98: 'fa',   # Iran
        212: 'ar',  # Morocco
        213: 'ar',  # Algeria
        216: 'ar',  # Tunisia
        218: 'ar',  # Libya
        220: 'en',  # Gambia
        221: 'fr',  # Senegal
        222: 'ar',  # Mauritania
        223: 'fr',  # Mali
        224: 'fr',  # Guinea
        225: 'fr',  # Ivory Coast
        226: 'fr',  # Burkina Faso
        227: 'fr',  # Niger
        228: 'fr',  # Togo
        229: 'fr',  # Benin
        230: 'en',  # Mauritius
        231: 'en',  # Liberia
        232: 'en',  # Sierra Leone
        233: 'en',  # Ghana
        234: 'en',   # Nigeria
        235: 'fr',  # Chad
        236: 'fr',  # Central African Republic
        237: 'fr',  # Cameroon
        238: 'pt',  # Cape Verde
        239: 'pt',  # Sao Tome and Principe
        240: 'es',  # Equatorial Guinea
        241: 'fr',  # Gabon
        242: 'fr',  # Republic of the Congo
        243: 'fr',  # Democratic Republic of the Congo
        244: 'pt',  # Angola
        245: 'pt',  # Guinea-Bissau
        246: 'en',  # British Indian Ocean Territory
        247: 'en',  # Ascension Island
        248: 'fr',  # Seychelles
        249: 'ar',  # Sudan
        250: 'rw',  # Rwanda
        251: 'am',  # Ethiopia
        252: 'so',  # Somalia
        253: 'fr',  # Djibouti
        254: 'sw',   # Kenya (Swahili)
        255: 'sw',   # Tanzania (Swahili)
        256: 'en',  # Uganda
        257: 'fr',  # Burundi
        258: 'pt',  # Mozambique
        260: 'en',  # Zambia
        261: 'fr',  # Madagascar
        262: 'fr',  # Réunion
        263: 'en',  # Zimbabwe
        264: 'en',  # Namibia
        265: 'en',  # Malawi
        266: 'en',  # Lesotho
        267: 'en',  # Botswana
        268: 'en',  # Eswatini
        269: 'fr',  # Comoros
        291: 'ti',  # Eritrea
        351: 'pt',  # Portugal
        352: 'fr',  # Luxembourg
        353: 'en',  # Ireland
        354: 'is',  # Iceland
        355: 'sq',  # Albania
        356: 'mt',  # Malta
        357: 'el',  # Cyprus
        358: 'fi',  # Finland
        359: 'bg',  # Bulgaria
        370: 'lt',  # Lithuania
        371: 'lv',  # Latvia
        372: 'et',  # Estonia
        373: 'ro',  # Moldova
        374: 'hy',  # Armenia
        375: 'be',  # Belarus
        376: 'ca',  # Andorra
        377: 'fr',  # Monaco
        378: 'it',  # San Marino
        379: 'la',  # Vatican City

        380: 'uk',  # Ukraine
        381: 'sr',  # Serbia
        382: 'sr',  # Montenegro
        383: 'sq',  # Kosovo
        385: 'hr',  # Croatia
        386: 'sl',  # Slovenia
        387: 'bs',  # Bosnia and Herzegovina
        389: 'mk',  # North Macedonia
        420: 'cs',  # Czech Republic
        421: 'sk',  # Slovakia
        423: 'de',  # Liechtenstein
        501: 'en',  # Belize
        502: 'es',  # Guatemala
        503: 'es',  # El Salvador
        504: 'es',  # Honduras
        505: 'es',  # Nicaragua
        506: 'es',  # Costa Rica
        507: 'es',  # Panama
        509: 'fr',  # Haiti
        591: 'es',  # Bolivia
        592: 'en',  # Guyana
        593: 'es',  # Ecuador
        594: 'fr',  # French Guiana
        595: 'es',  # Paraguay
        596: 'fr',  # Martinique
        597: 'nl',  # Suriname
        598: 'es',  # Uruguay
        599: 'nl',  # Curaçao
        670: 'pt',  # Timor-Leste
        672: 'en',  # Norfolk Island
        673: 'ms',  # Brunei
        674: 'en',  # Nauru
        675: 'en',  # Papua New Guinea
        676: 'to',  # Tonga
        677: 'en',  # Solomon Islands
        678: 'en',  # Vanuatu
        679: 'en',  # Fiji
        680: 'en',  # Palau
        681: 'fr',  # Wallis and Futuna
        682: 'en',  # Cook Islands
        683: 'en',  # Niue
        685: 'sm',  # Samoa
        686: 'en',  # Kiribati
        687: 'fr',  # New Caledonia
        688: 'en',  # Tuvalu
        689: 'fr',  # French Polynesia
        690: 'en',  # Tokelau
        691: 'en',  # Micronesia
        692: 'en',  # Marshall Islands
        850: 'ko',  # North Korea
        852: 'zh',   # Hong Kong
        853: 'zh',  # Macau
        855: 'km',  # Cambodia
        856: 'lo',  # Laos
        880: 'bn',  # Bangladesh
        886: 'zh',  # Taiwan
        960: 'dv',  # Maldives
        961: 'ar',  # Lebanon
        962: 'ar',  # Jordan
        963: 'ar',  # Syria
        964: 'ar',  # Iraq
        965: 'ar',  # Kuwait
        966: 'ar',  # Saudi Arabia
        967: 'ar',  # Yemen
        968: 'ar',  # Oman
        970: 'ar',  # Palestine
        971: 'ar',  # United Arab Emirates
        972: 'he',  # Israel
        973: 'ar',  # Bahrain
        974: 'ar',  # Qatar
        975: 'dz',  # Bhutan
        976: 'mn',  # Mongolia
        977: 'ne',  # Nepal
        992: 'tg',  # Tajikistan
        993: 'tk',  # Turkmenistan
        994: 'az',  # Azerbaijan
        995: 'ka',  # Georgia
        996: 'ky',  # Kyrgyzstan
        998: 'uz',  # Uzbekistan
        # Add more country codes and their primary languages here...
    }

        # Contains the translated messages. A random message is chosen from the list
        # to make the bot feel more dynamic and less repetitive.
        self.MESSAGES: Dict[str, Dict[str, List[str]]] = {
            'en': {
                'still_thinking': [
                    "One moment, I'm working on that for you...",
                    "Just a second, processing your request.",
                    "Working on it now!",
                    "Let me check on that for you...",
                ],
                'busy': [
                    "I'm still working on your previous request. I'll be with you shortly!",
                    "Please give me a moment to finish up your last message.",
                    "I can only handle one request at a time. I'll let you know when I'm done!",
                ],
            },
            'es': {
                'still_thinking': [
                    "Un momento, estoy trabajando en tu solicitud...",
                    "Un segundo, procesando tu petición.",
                    "¡Estoy en ello!",
                    "Déjame revisarlo por ti...",
                ],
                'busy': [
                    "Todavía estoy trabajando en tu solicitud anterior. ¡Te atenderé en breve!",
                    "Por favor, dame un momento para terminar con tu último mensaje.",
                    "Solo puedo atender una solicitud a la vez. ¡Te avisaré cuando termine!",
                ],
            },
            'fr': {
                'still_thinking': [
                    "Un instant, je m'en occupe...",
                    "Juste une seconde, je traite votre demande.",
                    "Je suis dessus !",
                    "Laissez-moi vérifier cela pour vous...",
                ],
                'busy': [
                    "Je travaille encore sur votre demande précédente. Je reviens vers vous bientôt !",
                    "Veuillez me donner un moment pour terminer votre dernier message.",
                    "Je ne peux traiter qu'une seule demande à la fois. Je vous préviendrai quand j'aurai fini !",
                ],
            },
            'de': {
                'still_thinking': [
                    "Einen Moment, ich arbeite daran...",
                    "Nur eine Sekunde, Ihre Anfrage wird bearbeitet.",
                    "Ich bin dabei!",
                    "Lassen Sie mich das für Sie prüfen...",
                ],
                'busy': [
                    "Ich bearbeite noch Ihre vorherige Anfrage. Ich bin gleich für Sie da!",
                    "Bitte geben Sie mir einen Moment, um Ihre letzte Nachricht zu beenden.",
                    "Ich kann nur eine Anfrage auf einmal bearbeiten. Ich melde mich, wenn ich fertig bin!",
                ],
            },
            'pt': {
                'still_thinking': [
                    "Um momento, estou trabalhando nisso para você...",
                    "Só um segundo, processando sua solicitação.",
                    "Estou trabalhando nisso agora!",
                    "Deixe-me verificar isso para você...",
                ],
                'busy': [
                    "Ainda estou trabalhando na sua solicitação anterior. Estarei com você em breve!",
                    "Por favor, me dê um momento para terminar sua última mensagem.",
                    "Só consigo lidar com uma solicitação de cada vez. Avisarei quando terminar!",
                ],
            },
            'hi': {
                'still_thinking': [
                    "एक क्षण, मैं आपके लिए उस पर काम कर रहा हूँ...",
                    "बस एक सेकंड, आपके अनुरोध पर कार्रवाई हो रही है।",
                    "अभी इस पर काम कर रहा हूँ!",
                    "मैं आपके लिए इसकी जांच करता हूँ...",
                ],
                'busy': [
                    "मैं अभी भी आपके पिछले अनुरोध पर काम कर रहा हूँ। मैं जल्द ही आपके साथ रहूँगा!",
                    "कृपया मुझे अपना पिछला संदेश समाप्त करने के लिए थोड़ा समय दें।",
                    "मैं एक समय में केवल एक ही अनुरोध संभाल सकता हूँ। जब मैं पूरा कर लूँगा तो आपको बता दूँगा!",
                ],
            },
            'sw': {
                'still_thinking': [
                    "Tafadhali subiri, ninashughulikia ombi lako...",
                    "Sekunde moja, ninachakata ombi lako.",
                    "Ninalifanyia kazi sasa hivi!",
                    "Acha nikuangalie...",
                ],
                'busy': [
                    "Bado ninashughulikia ombi lako la awali. Nitakuwa nawe hivi karibuni!",
                    "Tafadhali nipe muda nimalize ujumbe wako wa mwisho.",
                    "Ninaweza kushughulikia ombi moja tu kwa wakati mmoja. Nitakujulisha nitakapomaliza!",
                ],
            },
            'zh': {
                'still_thinking': [
                    "请稍等，我正在为您处理...",
                    "请稍候，正在处理您的请求。",
                    "我正在处理！",
                    "让我为您查一下...",
                ],
                'busy': [
                    "我还在处理您之前的请求。马上就好！",
                    "请给我一点时间处理完您的上一条消息。",
                    "我一次只能处理一个请求。完成后会通知您！",
                ],
            },
            'it': {
                'still_thinking': [
                    "Un momento, ci sto lavorando per te...",
                    "Solo un secondo, sto elaborando la tua richiesta.",
                    "Ci sto lavorando ora!",
                    "Lascia che controlli per te...",
                ],
                'busy': [
                    "Sto ancora lavorando alla tua richiesta precedente. Sarò da te a breve!",
                    "Per favore, dammi un momento per finire il tuo ultimo messaggio.",
                    "Posso gestire solo una richiesta alla volta. Ti farò sapere quando avrò finito!",
                ],
            },
            'ja': {
                'still_thinking': [
                    "少々お待ちください、今対応中です...",
                    "少しお待ちください、リクエストを処理しています。",
                    "ただいま対応中です！",
                    "確認させてください...",
                ],
                'busy': [
                    "まだ前のリクエストに対応中です。もうしばらくお待ちください！",
                    "前のメッセージが完了するまで、少々お待ちください。",
                    "一度に一つのリクエストしか対応できません。完了次第お知らせします！",
                ],
            },
            'ru': {
                'still_thinking': [
                    "Один момент, я работаю над этим для вас...",
                    "Секундочку, обрабатываю ваш запрос.",
                    "Сейчас работаю над этим!",
                    "Позвольте мне проверить это для вас...",
                ],
                'busy': [
                    "Я все еще работаю над вашим предыдущим запросом. Скоро буду с вами!",
                    "Пожалуйста, дайте мне минутку, чтобы закончить ваше последнее сообщение.",
                    "Я могу обрабатывать только один запрос за раз. Я сообщу вам, когда закончу!",
                ],
            },
            'ar': {
                'still_thinking': [
                    "لحظة من فضلك، أنا أعمل على ذلك من أجلك...",
                    "ثانية واحدة، جاري معالجة طلبك.",
                    "أعمل على ذلك الآن!",
                    "دعني أتحقق من ذلك من أجلك...",
                ],
                'busy': [
                    "ما زلت أعمل على طلبك السابق. سأكون معك قريبا!",
                    "من فضلك امنحني لحظة لإنهاء رسالتك الأخيرة.",
                    "يمكنني التعامل مع طلب واحد فقط في كل مرة. سأخبرك عندما أنتهي!",
                ],
            },
            'ko': {
                'still_thinking': [
                    "잠시만요, 작업 중입니다...",
                    "요청을 처리하는 중입니다. 잠시만 기다려 주세요.",
                    "지금 작업 중입니다!",
                    "확인해 보겠습니다...",
                ],
                'busy': [
                    "아직 이전 요청을 처리 중입니다. 곧 연락드리겠습니다!",
                    "마지막 메시지를 마무리할 시간을 잠시 주세요.",
                    "한 번에 하나의 요청만 처리할 수 있습니다. 완료되면 알려드리겠습니다!",
                ],
            },
            'tr': {
                'still_thinking': [
                    "Bir dakika, sizin için üzerinde çalışıyorum...",
                    "Bir saniye, isteğiniz işleniyor.",
                    "Şu anda üzerinde çalışıyorum!",
                    "Sizin için kontrol edeyim...",
                ],
                'busy': [
                    "Hala önceki isteğiniz üzerinde çalışıyorum. Kısa süre içinde sizinle olacağım!",
                    "Lütfen son mesajınızı bitirmem için bana bir dakika verin.",
                    "Aynı anda yalnızca bir isteği işleyebilirim. Bitirdiğimde size haber veririm!",
                ],
            },
            'nl': {
                'still_thinking': [
                    "Een ogenblik, ik ben er voor u mee bezig...",
                    "Een seconde, uw verzoek wordt verwerkt.",
                    "Ik werk er nu aan!",
                    "Laat me dat even voor u nakijken...",
                ],
                'busy': [
                    "Ik ben nog steeds bezig met uw vorige verzoek. Ik ben zo bij u!",
                    "Geef me alstublieft een moment om uw laatste bericht af te ronden.",
                    "Ik kan maar één verzoek tegelijk afhandelen. Ik laat het u weten als ik klaar ben!",
                ],
            },
        }
    
    def _get_lang_from_phone(self, phone_number: str) -> Optional[str]:
        """
        Parses a phone number to determine the language code from its country code.

        Args:
            phone_number: The full phone number in E.164 format (e.g., "+14155552671").

        Returns:
            The two-letter language code (e.g., 'en') or None if not found.
        """
        try:
            # The default_region='US' is a fallback for numbers without a country code.
            parsed_number = phonenumbers.parse(phone_number, None)
            country_code = parsed_number.country_code 
            if country_code is None:
                return None
            return self.COUNTRY_CODE_TO_LANG.get(country_code)
        except phonenumbers.phonenumberutil.NumberParseException:
            # Could not parse the number, so we can't determine the country.
            return None

    def _get_message(self, message_type: str, phone_number: str, user_lang: Optional[str] = None) -> str:
        """
        Internal logic to retrieve a localized message.

        It prioritizes the explicitly provided user_lang, then tries to infer
        from the phone number, and finally falls back to English.

        Args:
            message_type: The key for the message type (e.g., 'still_thinking').
            phone_number: The user's phone number.
            user_lang: An optional pre-defined language for the user (e.g., 'es').

        Returns:
            A randomly selected, localized message string.
        """
        lang_code = 'en'  # Default language

        if user_lang and user_lang in self.MESSAGES:
            # Use the language stored in the user's profile if it exists and is supported.
            lang_code = user_lang
        else:
            # Otherwise, try to infer from the phone number.
            inferred_lang = self._get_lang_from_phone(phone_number)
            if inferred_lang and inferred_lang in self.MESSAGES:
                lang_code = inferred_lang

        # Get the list of possible messages for the determined language and type.
        message_list = self.MESSAGES.get(lang_code, {}).get(message_type, [])

        # Fallback to English if the specific message type is not translated for the language.
        if not message_list:
            message_list = self.MESSAGES.get('en', {}).get(message_type, ["Please wait..."])

        return random.choice(message_list)

    def get_still_thinking_message(self, phone_number: str, user_lang: Optional[str] = None) -> str:
        """
        Gets a random "please wait, I'm working on it" message in the user's language.

        Args:
            phone_number: The user's full phone number.
            user_lang: Optional language code if known from the user's profile.

        Returns:
            A localized message string.
        """
        return self._get_message('still_thinking', phone_number, user_lang)

    def get_busy_message(self, phone_number: str, user_lang: Optional[str] = None) -> str:
        """
        Gets a random "I'm busy with your last request" message in the user's language.

        Args:
            phone_number: The user's full phone number.
            user_lang: Optional language code if known from the user's profile.

        Returns:
            A localized message string.
        """
        return self._get_message('busy', phone_number, user_lang)