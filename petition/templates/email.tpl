Denní zpráva aplikace Petice (čas vytvoření: {{ time }}):
{% for p in petitions %}
Nové podpisy pod peticí "{{ p.longname }}":
{% for s in p.signatures %}   {{ s.name }}{% if s.occupation %}, {{ s.occupation }}{% endif %}{% if address %}, {{ s.address }}{% endif %}{% if s.note %} ({{ s.note }}){% endif %}
{% empty %}   Žádné nové podpisy.{% endfor %}
   Nyní je pod touto peticí celkem {{ p.total }} podpisů.
{% endfor %}
E-mailový robot aplikace Petice ({{ url }})
