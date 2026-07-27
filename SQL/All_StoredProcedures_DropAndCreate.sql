USE [CycloneRCM_DEV_Ranie]
GO

-- =============================================
-- Combined Script: Drop and Create All Stored Procedures
-- Author: Ranie
-- Date: Generated Script
-- Description: Drops and recreates all ClearingHouse stored procedures
-- =============================================

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- =============================================
-- 1. Insert_ClearingHouseHeader
-- =============================================
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Insert_ClearingHouseHeader]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Insert_ClearingHouseHeader]
GO

CREATE PROCEDURE [dbo].[Insert_ClearingHouseHeader] 
	@FileName varchar(500),
	@FileType varchar(10),
	@ClearingHouseHeaderId int out
AS
BEGIN
	IF NOT EXISTS(SELECT ClearingHouseHeaderId FROM ClearingHouseHeader WHERE FileName = @FileName AND FileType = @FileType)
	BEGIN
		INSERT INTO ClearingHouseHeader(FileName,FileType,ProcessDate)
		VALUES(@FileName,@FileType,GETDATE())

		SET @ClearingHouseHeaderId = @@IDENTITY
	END
END
GO

-- =============================================
-- 2. IsExist_ClearingHouseHeader
-- =============================================
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[IsExist_ClearingHouseHeader]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[IsExist_ClearingHouseHeader]
GO

CREATE PROCEDURE [dbo].[IsExist_ClearingHouseHeader] 
	@FileName varchar(500),
	@FileType varchar(10),
	@IsExist bit out
AS
BEGIN
	IF EXISTS(SELECT ClearingHouseHeaderId FROM ClearingHouseHeader WHERE FileName = @FileName AND FileType = @FileType)
	BEGIN
		SET @IsExist = 1		
	END
	ELSE
	BEGIN
		SET @IsExist = 0
	END
END
GO

-- =============================================
-- 3. Insert_ClearingHouse277
-- =============================================
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Insert_ClearingHouse277]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Insert_ClearingHouse277]
GO

CREATE PROCEDURE [dbo].[Insert_ClearingHouse277]
	@ClearingHouseHeaderId int,
	@FileName_277 varchar(500),
	@GroupControlNumber varchar(50),
	@TranDate datetime,
	@PatientAccNo varchar(50),
	@ClaimStatusCatCode varchar(5),
	@ClaimStatusCode varchar(5),
	@Remarks text=null,
	@Status varchar(5),
	@Submitter varchar(50),
	@InsuredId varchar(50)
AS
BEGIN
	INSERT INTO ClearingHouse277(ClearingHouseHeaderId,FileName_277,GroupControlNumber,TranDate,PatientAccNo,ClaimStatusCatCode,ClaimStatusCode,Remarks,
		Status,Submitter,InsuredId,ProcessedDateTime)
	VALUES(@ClearingHouseHeaderId,@FileName_277,@GroupControlNumber,@TranDate,@PatientAccNo,@ClaimStatusCatCode,@ClaimStatusCode,@Remarks,
		@Status,@Submitter,@InsuredId,GETDATE())
END
GO

-- =============================================
-- 4. Insert_ClearingHouse999
-- =============================================
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Insert_ClearingHouse999]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Insert_ClearingHouse999]
GO

CREATE PROCEDURE [dbo].[Insert_ClearingHouse999]
	@ClearingHouseHeaderId int,
	@FileName999 varchar(500),	
	@GroupControlNumber varchar(50),
	@GroupControlID varchar(50),
	@PatientNo varchar(50),
	@Status999 varchar(10)
AS
BEGIN
	IF NOT EXISTS(SELECT Id FROM ClearingHouse999 WHERE FileName999 = @FileName999 AND GroupControlNumber = @GroupControlNumber AND PatientNo = @PatientNo)
	BEGIN
		INSERT INTO ClearingHouse999(ClearingHouseHeaderId,FileName999,GroupControlNumber,GroupControlID,PatientNo,Status999)
		VALUES(@ClearingHouseHeaderId,@FileName999,@GroupControlNumber,@GroupControlID,@PatientNo,@Status999)
	END
END
GO

-- =============================================
-- 5. Insert_ClearingHouse835Master
-- =============================================
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Insert_ClearingHouse835Master]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Insert_ClearingHouse835Master]
GO

CREATE PROCEDURE [dbo].[Insert_ClearingHouse835Master]
	@ClearingHouseHeaderId int,
	@Filename_835 varchar(500),
	@GroupControlNumber varchar(50),
	@Checkdate datetime,
	@CheckNumber varchar(50),
	@TotalPayment varchar(5),
	@Paymentmethod varchar(5),
	@Productiondate datetime,
	@PayerName varchar(500),
	@PayerAddress varchar(500),
	@PayerCity varchar(50),
	@PayerState varchar(10),
	@PayerZipcode varchar(10),
	@Payee varchar(500),
	@ClearingHouse835MasterId int out
AS
BEGIN
	INSERT INTO ClearingHouse835Master(ClearingHouseHeaderId,Filename_835,GroupControlNumber,Checkdate,CheckNumber,TotalPayment,Paymentmethod,Productiondate,PayerName,PayerAddress,PayerCity,PayerState,PayerZipcode,Payee)
	VALUES(@ClearingHouseHeaderId,@Filename_835,@GroupControlNumber,@Checkdate,@CheckNumber,@TotalPayment,@Paymentmethod,@Productiondate,@PayerName,@PayerAddress,@PayerCity,@PayerState,@PayerZipcode,@Payee)

	SET @ClearingHouse835MasterId = @@IDENTITY
END
GO

-- =============================================
-- 6. Insert_ClearingHouse835Patient
-- =============================================
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Insert_ClearingHouse835Patient]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Insert_ClearingHouse835Patient]
GO

CREATE PROCEDURE [dbo].[Insert_ClearingHouse835Patient]
	@ClearingHouse835Id int,
	@PatientAccNo varchar(50),
	@Claimstatuscode varchar(50),
	@TotalClaimChrgAmt varchar(50),
	@ClaimPaymentAmt varchar(5),
	@FacilityTypeCode varchar(5),
	@PayerClaimControlNumber varchar(50),
	@PatientFirstName varchar(50),
	@PatientLastName varchar(50),
	@ClearingHouse835PatientId int out
AS
BEGIN
	INSERT INTO ClearingHouse835Patient(ClearingHouse835Id,PatientAccNo,Claimstatuscode,TotalClaimChrgAmt,ClaimPaymentAmt,FacilityTypeCode,PayerClaimControlNumber,PatientFirstName,PatientLastName)
	VALUES(@ClearingHouse835Id,@PatientAccNo,@Claimstatuscode,@TotalClaimChrgAmt,@ClaimPaymentAmt,@FacilityTypeCode,@PayerClaimControlNumber,@PatientFirstName,@PatientLastName)

	SET @ClearingHouse835PatientId = @@IDENTITY
END
GO

-- =============================================
-- 7. Insert_ClearingHouse835Service
-- =============================================
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Insert_ClearingHouse835Service]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Insert_ClearingHouse835Service]
GO

CREATE PROCEDURE [dbo].[Insert_ClearingHouse835Service]
	@ClearingHouse835PatientId int,
	@ServiceCode varchar(50),
	@ServiceChrgAmt varchar(50),
	@ServiceProviderPayment varchar(50),
	@Units int,
	@ServiceDate datetime,
	@ClearingHouse835ServiceId int out
AS
BEGIN
	INSERT INTO ClearingHouse835Service(ClearingHouse835PatientId,ServiceCode,ServiceChrgAmt,ServiceProviderPayment,Units,ServiceDate)
	VALUES(@ClearingHouse835PatientId,@ServiceCode,@ServiceChrgAmt,@ServiceProviderPayment,@Units,@ServiceDate)

	SET @ClearingHouse835ServiceId = @@IDENTITY
END
GO

-- =============================================
-- 8. Insert_ClearingHouse835Adjustment
-- =============================================
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Insert_ClearingHouse835Adjustment]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Insert_ClearingHouse835Adjustment]
GO

CREATE PROCEDURE [dbo].[Insert_ClearingHouse835Adjustment]
	@ClearingHouse835ServiceId int,
	@AdjustmentGroupCode varchar(50),
	@AdjustmentAmount varchar(50),
	@AdjustmentReasonCode varchar(50),
	@ClearingHouse835AdjustmentId int out
AS
BEGIN
	INSERT INTO ClearingHouse835Adjustment(ClearingHouse835ServiceId,AdjustmentGroupCode,AdjustmentAmount,AdjustmentReasonCode)
	VALUES(@ClearingHouse835ServiceId,@AdjustmentGroupCode,@AdjustmentAmount,@AdjustmentReasonCode)

	SET @ClearingHouse835AdjustmentId = @@IDENTITY
END
GO

-- =============================================
-- 9. Insert_ClearingHouse835ServiceRemark
-- =============================================
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Insert_ClearingHouse835ServiceRemark]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Insert_ClearingHouse835ServiceRemark]
GO

CREATE PROCEDURE [dbo].[Insert_ClearingHouse835ServiceRemark]
	@ClearingHouse835ServiceId int,
	@RemarksCode varchar(50),
	@ClearingHouse835ServiceRemarkId int out
AS
BEGIN
	INSERT INTO ClearingHouse835ServiceRemark(ClearingHouse835ServiceId,RemarksCode)
	VALUES(@ClearingHouse835ServiceId,@RemarksCode)

	SET @ClearingHouse835ServiceRemarkId = @@IDENTITY
END
GO

-- =============================================
-- 10. Insert_ClearingHouseErrorLog
-- =============================================
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Insert_ClearingHouseErrorLog]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Insert_ClearingHouseErrorLog]
GO

CREATE PROCEDURE [dbo].[Insert_ClearingHouseErrorLog]
	@FileName varchar(500),
	@FunctionName varchar(100),
	@Error varchar(max)
AS
BEGIN
	INSERT INTO ClearingHouseErrorLog(FileName,FunctionName,Error)
	VALUES(@FileName,@FunctionName,@Error)
END
GO


