<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:eats="http://hdl.handle.net/10063/234"
                xmlns:eac="urn:isbn:1-931666-33-4"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                exclude-result-prefixes="eats"
                version="1.0">

  <!-- Templates for transforming the EATSML for a specific entity
       into EAC-CPF. This XSLT is designed to be imported by another
       XSLT that kicks off the transformation.
       
       This XSLT requires a base_url global variable/parameter from
       its importer. -->

  <!-- eac:eac-cpf -->
  <xsl:template match="eats:entity">
    <xsl:param name="authority-record-id"/>
    <xsl:variable name="full-authority-record-id" select="concat('authority_record-', $authority-record-id)"/>
    <xsl:variable name="authority-record" select="id($full-authority-record-id)"/>
    <xsl:variable name="authority" select="id($authority-record/@authority)"/>
    <eac:eac-cpf>
      <xsl:apply-templates select="." mode="control">
        <xsl:with-param name="full-authority-record-id" select="$full-authority-record-id"/>
        <xsl:with-param name="authority-record" select="$authority-record"/>
        <xsl:with-param name="authority" select="$authority"/>
      </xsl:apply-templates>
      <xsl:apply-templates select="." mode="cpf-description">
        <xsl:with-param name="full-authority-record-id" select="$full-authority-record-id"/>
        <xsl:with-param name="authority-record" select="$authority-record"/>
        <xsl:with-param name="authority" select="$authority"/>
      </xsl:apply-templates>
    </eac:eac-cpf>
  </xsl:template>

  <!-- eac:control -->
  <xsl:template match="eats:entity" mode="control">
    <xsl:param name="full-authority-record-id"/>
    <xsl:param name="authority-record"/>
    <xsl:param name="authority"/>
    <eac:control>
      <xsl:call-template name="get-record-id">
        <xsl:with-param name="entity-id" select="@eats_id"/>
        <xsl:with-param name="authority-record" select="$authority-record"/>
      </xsl:call-template>
      <eac:maintenanceStatus>
        <xsl:text>revised</xsl:text>
      </eac:maintenanceStatus>
      <eac:maintenanceAgency>
        <xsl:choose>
          <xsl:when test="$authority/eats:name = 'Auckland War Memorial Museum'">
            <eac:agencyCode>NZ-AR</eac:agencyCode>
          </xsl:when>
          <xsl:when test="$authority/eats:name = 'New Zealand Electronic Text Centre'">
            <eac:agencyCode>NZ-WU</eac:agencyCode>
          </xsl:when>
          <xsl:when test="$authority/eats:name = 'Dictionary of New Zealand Biography'">
            <eac:agencyCode>NZ-WCUL</eac:agencyCode>
          </xsl:when>
          <xsl:when test="$authority/eats:name = 'National Library of New Zealand'">
            <eac:agencyCode>NZ-WN</eac:agencyCode>
          </xsl:when>
        </xsl:choose>
        <eac:agencyName>
          <xsl:value-of select="$authority/eats:name"/>
        </eac:agencyName>
      </eac:maintenanceAgency>
      <eac:maintenanceHistory>
        <eac:maintenanceEvent>
          <eac:eventType>revised</eac:eventType>
          <eac:eventDateTime>
            <xsl:attribute name="standardDateTime">
              <xsl:value-of select="@last_modified"/>
            </xsl:attribute>
          </eac:eventDateTime>
          <eac:agentType>machine</eac:agentType>
          <eac:agent>
            <xsl:text>Entity Authority Tool Set at http://</xsl:text>
            <xsl:value-of select="$base_url"/>
          </eac:agent>
        </eac:maintenanceEvent>
      </eac:maintenanceHistory>
    </eac:control>
  </xsl:template>    

  <!-- eac:recordId and eac:otherRecordId -->
  <xsl:template name="get-record-id">
    <!-- EAC-CPF does not allow eac:recordId to contain a URL, but
         eac:otherRecordId can. -->
    <xsl:param name="entity-id"/>
    <xsl:param name="authority-record"/>
    <eac:recordId>
      <xsl:value-of select="$entity-id"/>
      <xsl:text>-</xsl:text>
      <xsl:value-of select="$authority-record/@eats_id"/>
    </eac:recordId>
    <eac:otherRecordId>
      <xsl:call-template name="get-record-url">
        <xsl:with-param name="entity-id" select="$entity-id"/>
        <xsl:with-param name="authority-record" select="$authority-record"/>
      </xsl:call-template>
    </eac:otherRecordId>
  </xsl:template>

  <xsl:template name="get-record-url">
    <xsl:param name="entity-id"/>
    <xsl:param name="authority-record"/>
    <xsl:text>http://</xsl:text>
    <xsl:value-of select="$base_url"/>
    <xsl:text>/</xsl:text>
    <xsl:value-of select="$entity-id"/>
    <xsl:text>/eac/</xsl:text>
    <xsl:value-of select="$authority-record/@eats_id"/>
    <xsl:text>/</xsl:text>
  </xsl:template>
  
  <!-- eac:cpfDescription -->
  <xsl:template match="eats:entity" mode="cpf-description">
    <xsl:param name="full-authority-record-id"/>
    <xsl:param name="authority-record"/>
    <xsl:param name="authority"/>
    <xsl:variable name="entity-notes" select="eats:entity_note_assertions/eats:entity_note_assertion[@authority_record=$full-authority-record-id]"/>
    <eac:cpfDescription>
      <eac:identity>
        <xsl:apply-templates select="$authority-record" mode="entityId">
          <xsl:with-param name="authority" select="$authority"/>
        </xsl:apply-templates>
        <xsl:apply-templates select="eats:entity_type_assertions">
          <xsl:with-param name="full-authority-record-id" select="$full-authority-record-id"/>
        </xsl:apply-templates>
        <!-- Completely ignore the possibility of creating nameEntryParallel elements for now. -->
        <xsl:apply-templates select="eats:name_assertions/eats:name_assertion[@authority_record=$full-authority-record-id]"/>
        <xsl:if test="$authority/eats:name != 'Dictionary of New Zealand Biography' and $entity-notes">
          <eac:descriptiveNote>
            <xsl:apply-templates select="$entity-notes"/>
          </eac:descriptiveNote>
        </xsl:if>
      </eac:identity>
      <xsl:variable name="existence-dates" select="eats:existence_assertions/eats:existence_assertion[@authority_record=$full-authority-record-id]/eats:dates"/>
      <xsl:if test="$existence-dates or ($authority/eats:name = 'Dictionary of New Zealand Biography' and $entity-notes)">
        <eac:description>
          <xsl:apply-templates select="$existence-dates"/>
          <xsl:if test="$authority/eats:name = 'Dictionary of New Zealand Biography' and $entity-notes">
            <eac:biogHist>
              <xsl:apply-templates select="$entity-notes"/>
            </eac:biogHist>
          </xsl:if>
        </eac:description>
      </xsl:if>
      <!-- QAZ: Relationships are problematic, since it's not clear
           which authority record assertions they are associated with
           on the related entity. Probably the best approach is to
           create a relationship to each record based on the same
           authority. -->
      <!-- QAZ: Reverse relationships present a problem, since they
           will be associated, most likely, with a different authority
           record than that we are handling here. Therefore ignore
           them for now, since they will turn up on the related
           record. Obviously this is not ideal, but is part of the
           wider design flaw of relationships. -->
      <!--<xsl:variable name="entity-relationships" select="$entity/eats:entity_relationship_assertions/eats:entity_relationship_assertion[@authority_record=$full-authority-record-id]"/>
      <xsl:variable name="reverse-entity-relationships" select="$entity/../eats:entity/eats:entity_relationship_assertions/eats:entity_relationship_assertion[@related_entity=concat('entity-', $entity_id)]"/>
      <xsl:if test="$entity-relationships or $reverse-entity-relationships">
        <eac:relations>
          <xsl:apply-templates select="$entity-relationships"/>
          <xsl:apply-templates select="$reverse-entity-relationships"/>
        </eac:relations>
      </xsl:if>-->
      <!-- Implement connections between multiple EAC-CPF records for
           the same entity via an identity cpfRelation. -->
      <xsl:variable name="other-records" select="eats:existence_assertions/eats:existence_assertion[not(@authority_record = $full-authority-record-id)][not(@authority_record = preceding-sibling::*/@authority_record)]"/>
      <xsl:if test="$other-records">
        <eac:relations>
          <xsl:apply-templates select="$other-records" mode="other-records">
            <xsl:with-param name="entity-id" select="@eats_id"/>
          </xsl:apply-templates>
        </eac:relations>
      </xsl:if>
    </eac:cpfDescription>
  </xsl:template>

  <!-- eac:entityId -->
  <xsl:template match="eats:authority_record/eats:authority_system_id" mode="entityId">
    <xsl:param name="authority"/>
    <eac:entityId>
      <xsl:if test="@is_complete='false'">
        <xsl:value-of select="$authority/eats:base_id"/>
      </xsl:if>
      <xsl:value-of select="."/>
    </eac:entityId>
  </xsl:template>
  <xsl:template match="eats:authority_record/eats:authority_system_url" mode="entityId">
    <xsl:param name="authority"/>
    <eac:entityId>
      <xsl:if test="@is_complete='false'">
        <xsl:value-of select="$authority/eats:base_url"/>
      </xsl:if>
      <xsl:value-of select="."/>
    </eac:entityId>
  </xsl:template>
  
  <!-- eac:entityType -->
  <xsl:template match="eats:entity_type_assertions">
    <xsl:param name="full-authority-record-id"/>
    <xsl:variable name="entity-type">
      <xsl:call-template name="get-entity-type">
        <xsl:with-param name="entity-type-assertion" select="eats:entity_type_assertion[@authority_record=$full-authority-record-id][1]"/>
      </xsl:call-template>
    </xsl:variable>
    <!-- Note that if this test evaluates to false, the resultant
         EAC-CPF document will be invalid, as eac:entityType is
         required. -->
    <xsl:if test="normalize-space($entity-type)">
      <eac:entityType>
        <xsl:value-of select="$entity-type"/>
      </eac:entityType>
    </xsl:if>
  </xsl:template>

  <xsl:template name="get-entity-type">
    <!-- Dereference the entity type. If it is one of "person",
         "family", or "organisation", use it, otherwise move on to the
         next applicable entity_type_assertion if there is one. -->
    <xsl:param name="entity-type-assertion"/>
    <xsl:if test="$entity-type-assertion">
      <xsl:variable name="entity-type" select="string(id($entity-type-assertion/@entity_type))"/>
      <xsl:choose>
        <xsl:when test="$entity-type = 'person'">
          <xsl:text>person</xsl:text>
        </xsl:when>
        <xsl:when test="$entity-type = 'family'">
          <xsl:text>family</xsl:text>
        </xsl:when>
        <xsl:when test="$entity-type = 'organisation'">
          <xsl:text>corporateBody</xsl:text>
        </xsl:when>
        <xsl:otherwise>
          <xsl:call-template name="get-entity-type">
            <xsl:with-param name="entity-type-assertion" select="$entity-type-assertion/following-sibling::*[@authority_record=current()/@authority_record][1]"/>
          </xsl:call-template>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:if>
  </xsl:template>

  <!-- eac:nameEntry -->
  <xsl:template match="eats:name_assertion">
    <eac:nameEntry>
      <xsl:call-template name="set-name">
        <xsl:with-param name="name-assertion" select="."/>
      </xsl:call-template>
      <xsl:apply-templates select="eats:dates"/>
    </eac:nameEntry>
  </xsl:template>

  <xsl:template name="set-name">
    <xsl:param name="name-assertion"/>
    <xsl:attribute name="xml:lang">
      <xsl:value-of select="id($name-assertion/@language)/eats:code"/>
    </xsl:attribute>
    <xsl:attribute name="scriptCode">
      <xsl:value-of select="id($name-assertion/@script)/eats:code"/>
    </xsl:attribute>
    <xsl:choose>
      <xsl:when test="normalize-space($name-assertion/eats:display_form)">
        <xsl:apply-templates select="$name-assertion/eats:display_form"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:apply-templates select="$name-assertion/eats:name_parts/eats:name_part"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- eac:part -->
  <xsl:template match="eats:display_form">
    <eac:part>
      <xsl:value-of select="."/>
    </eac:part>
  </xsl:template>
  <xsl:template match="eats:name_part">
    <eac:part>
      <!-- The value of localType should be an absolute URI. EATS
           should allow for/expose URLs for its infrastructural
           elements. -->
      <xsl:attribute name="localType">
        <xsl:value-of select="translate(id(id(@type)/@system_name_part_type)/eats:name, ' ', '-')"/>
      </xsl:attribute>
      <xsl:if test="@language">
        <xsl:attribute name="xml:lang">
          <xsl:value-of select="id(@language)/eats:code"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:value-of select="."/>
    </eac:part>
  </xsl:template>

  <!-- eac:identity/eac:descriptiveNote/eac:p -->
  <xsl:template match="eats:entity_note_assertion">
    <eac:p>
      <xsl:value-of select="."/>
    </eac:p>
  </xsl:template>

  <!-- eac:existDates -->
  <xsl:template match="eats:existence_assertion/eats:dates">
    <eac:existDates>
      <xsl:choose>
        <xsl:when test="count(eats:date) &gt; 1">
          <eac:dateSet>
            <xsl:apply-templates/>
          </eac:dateSet>
        </xsl:when>
        <xsl:otherwise>
          <xsl:apply-templates/>
        </xsl:otherwise>
      </xsl:choose>
    </eac:existDates>
  </xsl:template>

  <!-- eac:useDates -->
  <xsl:template match="eats:name_assertion/eats:dates">
    <eac:useDates>
      <xsl:choose>
        <xsl:when test="count(eats:date) &gt; 1">
          <eac:dateSet>
            <xsl:apply-templates/>
          </eac:dateSet>
        </xsl:when>
        <xsl:otherwise>
          <xsl:apply-templates/>
        </xsl:otherwise>
      </xsl:choose>
    </eac:useDates>
  </xsl:template>
  
  <!-- eac:date and eac:dateRange -->
  <xsl:template match="eats:date">
    <xsl:choose>
      <xsl:when test="eats:date_part/@type='point_date'">
        <xsl:variable name="point-date" select="eats:date_part[@type='point_date']"/>
        <eac:date standardDate="{$point-date/eats:normalised}">
          <xsl:value-of select="$point-date/eats:raw"/>
        </eac:date>
      </xsl:when>
      <xsl:when test="eats:date_part[@type='start_date' or @type='end_date' or @type='start_terminus_post' or @type='start_terminus_ante' or @type='end_terminus_post' or @type='end_terminus_ante']">
        <eac:dateRange>
          <xsl:if test="eats:date_part[@type='start_date' or @type='start_terminus_post' or @type='start_terminus_ante']">
            <eac:fromDate>
              <xsl:apply-templates select="eats:date_part[@type='start_date' or @type='start_terminus_post' or @type='start_terminus_ante']"/>
            </eac:fromDate>
          </xsl:if>
          <xsl:if test="eats:date_part[@type='end_date' or @type='end_terminus_post' or @type='end_terminus_ante']">
            <eac:toDate>
              <xsl:apply-templates select="eats:date_part[@type='end_date' or @type='end_terminus_post' or @type='end_terminus_ante']"/>
            </eac:toDate>
          </xsl:if>
        </eac:dateRange>
      </xsl:when>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="eats:date_part[@type='start_date' or @type='end_date']">
    <xsl:attribute name="standardDate">
      <xsl:value-of select="eats:normalised"/>
    </xsl:attribute>
    <xsl:value-of select="eats:raw"/>
  </xsl:template>

  <xsl:template match="eats:date_part[@type='start_terminus_post' or @type='end_terminus_post']">
    <xsl:attribute name="notBefore">
      <xsl:value-of select="eats:normalised"/>
    </xsl:attribute>
  </xsl:template>

  <xsl:template match="eats:date_part[@type='start_terminus_ante' or @type='end_terminus_ante']">
    <xsl:attribute name="notAfter">
      <xsl:value-of select="eats:normalised"/>
    </xsl:attribute>
  </xsl:template>
  
  <!-- eac:cpfRelation -->
  <xsl:template match="eats:entity_relationship_assertion">
    <!-- Use eac:cpfRelation only if the related entity type is suitable. -->
    <xsl:variable name="is-reverse">
      <xsl:choose>
        <xsl:when test="@related_entity = concat('entity-', $entity_id)">
          <xsl:value-of select="1"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="0"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="related-entity-id">
      <xsl:choose>
        <xsl:when test="number($is-reverse)">
          <xsl:value-of select="../../@xml:id"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="@related_entity"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="related-entity-type">
      <xsl:call-template name="get-entity-type">
        <xsl:with-param name="entity-type-assertion" select="id($related-entity-id)/eats:entity_type_assertions/eats:entity_type_assertion[1]"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:if test="$related-entity-type">
      <eac:cpfRelation xlink:type="simple" relatedCpfEntityType="{$related-entity-type}">
        <xsl:attribute name="xlink:href">
          <xsl:text>http://</xsl:text>
          <xsl:value-of select="concat($base_url, '/', substring-after($related-entity-id, 'entity-'), '/')"/>
        </xsl:attribute>
        <xsl:call-template name="set-relationship-type">
          <xsl:with-param name="type" select="id(@type)"/>
          <xsl:with-param name="is-reverse" select="number($is-reverse)"/>
        </xsl:call-template>
        <eac:relationEntry>
          <xsl:call-template name="set-name">
            <xsl:with-param name="name-assertion" select="id($related-entity-id)/eats:name_assertions/eats:name_assertion[1]"/>
          </xsl:call-template>
        </eac:relationEntry>
      </eac:cpfRelation>
    </xsl:if>
  </xsl:template>

  <xsl:template name="set-relationship-type">
    <xsl:param name="type"/>
    <xsl:param name="is-reverse"/>
    <!-- QAZ: Is this a hack? Oh I think it is. EATS needs to have the
         facility to have all type information reference zero or more
         URIs defining/representing the type. It wouldn't help
         entirely in this case, but it would be a start. -->
    <xsl:choose>
      <xsl:when test="string($type) = 'is a child of'">
        <xsl:attribute name="cpfRelationType">
          <xsl:text>family</xsl:text>
        </xsl:attribute>
        <xsl:attribute name="xlink:arcrole">
          <xsl:choose>
            <xsl:when test="$is-reverse">
              <xsl:text>parent</xsl:text>
            </xsl:when>
            <xsl:otherwise>
              <xsl:text>child</xsl:text>
            </xsl:otherwise>
          </xsl:choose>
        </xsl:attribute>
      </xsl:when>
      <xsl:when test="string($type) = 'is a sibling of'">
        <xsl:attribute name="cpfRelationType">
          <xsl:text>family</xsl:text>
        </xsl:attribute>
        <xsl:attribute name="xlink:arcrole">
          <xsl:text>sibling</xsl:text>
        </xsl:attribute>
      </xsl:when>
      <xsl:when test="string($type) = 'is a descendant of'">
        <xsl:attribute name="cpfRelationType">
          <xsl:text>family</xsl:text>
        </xsl:attribute>
        <xsl:attribute name="xlink:arcrole">
          <xsl:choose>
            <xsl:when test="$is-reverse">
              <xsl:text>ancestor</xsl:text>
            </xsl:when>
            <xsl:otherwise>
              <xsl:text>descendant</xsl:text>
            </xsl:otherwise>
          </xsl:choose>
        </xsl:attribute>
      </xsl:when>
    </xsl:choose>
  </xsl:template>
  
  <xsl:template match="eats:existence_assertion" mode="other-records">
    <xsl:param name="entity-id"/>
    <xsl:variable name="entity-type">
      <xsl:call-template name="get-entity-type">
        <xsl:with-param name="entity-type-assertion" select="../../eats:entity_type_assertions/eats:entity_type_assertion[@authority_record=current()/@authority_record][1]"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:if test="normalize-space($entity-type)">
      <eac:cpfRelation cpfRelationType="identity">
        <xsl:attribute name="xlink:href">
          <xsl:call-template name="get-record-url">
            <xsl:with-param name="entity-id" select="$entity-id"/>
            <xsl:with-param name="authority-record" select="id(@authority_record)"/>
          </xsl:call-template>
        </xsl:attribute>
      </eac:cpfRelation>
    </xsl:if>
  </xsl:template>

</xsl:stylesheet>