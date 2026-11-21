"""Optional language-model gateway. Off unless COCKPIT_AI=claude is set on the cockpit machine.

Every request passes the local mask first; if anything personal is still detectable, nothing is sent.
Only masked documents and aggregate tables can reach this module; it never sees case rows.
"""
import os

from . import redact

MODEL = 'claude-opus-5-5'
SYSTEM = ('You support the asylum social service of the City of Bern. You receive masked documents or '
          'aggregate statistics only; placeholders like [NAME] stand for removed personal data and must never be guessed. '
          'Be factual and brief, separate observation from recommendation, and call group differences associations, not causes. '
          'Answer in {language}.')
LANGUAGES = ('German (Swiss spelling, no ß)','English','French')


def status():
    if os.getenv('COCKPIT_AI')!='claude':
        return 'off'
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return 'missing_sdk'
    return 'claude'


def ask(lang, instruction, material, known_ids=()):
    """Returns (answer or None, report). The report lists what was masked and why a request did not run."""
    masked,counts = redact.mask(material,known_ids)
    report = {'masked':counts,'sent':masked,'state':status()}
    leftovers = redact.leaks(masked)
    if leftovers:
        report['state'] = 'blocked'
        report['leaks'] = leftovers
        return None,report
    if report['state']!='claude':
        return None,report
    import anthropic
    client = anthropic.Anthropic(timeout=60.0,max_retries=1)
    try:
        response = client.beta.messages.create(
            model=MODEL,max_tokens=4000,
            betas=['server-side-fallback-2026-07-01'],fallbacks='default',
            output_config={'effort':'low'},
            system=SYSTEM.format(language=LANGUAGES[lang]),
            messages=[{'role':'user','content':f'{instruction}\n\n<material>\n{masked}\n</material>'}])
    except anthropic.RateLimitError:
        report['state'] = 'rate_limited'
        return None,report
    except anthropic.APIStatusError as error:
        report['state'] = f'api_error_{error.status_code}'
        return None,report
    except anthropic.APIConnectionError:
        report['state'] = 'offline'
        return None,report
    if response.stop_reason=='refusal':
        report['state'] = 'refused'
        return None,report
    answer = ''.join(block.text for block in response.content if block.type=='text').strip()
    report['state'] = 'answered'
    return answer or None,report
